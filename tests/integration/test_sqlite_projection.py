import os
import sqlite3
from pathlib import Path

import pytest

from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork


def fixture_record():
    fixture_root = Path(__file__).parents[1] / "fixtures"
    return MarkdownInvestigationRepository(fixture_root).load("inv_mass_question")


def test_projection_preserves_resumable_state_and_relationships(tmp_path: Path) -> None:
    record = fixture_record()
    database_path = tmp_path / "data" / "forge.sqlite3"
    projection = SQLiteProjection(database_path)

    projection.save(record)

    assert projection.load_record(record.id) == record
    assert projection.count_investigations() == 1
    assert set(projection.relationships(record.id)) == {
        ("epi_nonzero_mass", "depends_on", record.id, "epi_closed_system"),
        ("epi_nonzero_mass", "depends_on", record.id, "epi_mass_reading"),
        ("epi_nonzero_mass", "supports", record.id, "epi_mass_reading"),
        ("epi_temperature_connection", "based_on", record.id, "epi_mass_reading"),
    }
    assert os.stat(database_path.parent).st_mode & 0o777 == 0o700
    assert os.stat(database_path).st_mode & 0o777 == 0o600


def test_search_finds_items_by_text_and_category(tmp_path: Path) -> None:
    record = fixture_record()
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    projection.save(record)

    exploratory_hits = projection.search("temperature", category="exploratory_item")
    evidence_hits = projection.search("sample", category="evidence")

    assert tuple(hit.item_id for hit in exploratory_hits) == ("epi_temperature_connection",)
    assert tuple(hit.category for hit in exploratory_hits) == ("exploratory_item",)
    assert tuple(hit.item_id for hit in evidence_hits) == ("epi_mass_reading",)


def test_search_treats_sql_metacharacters_as_literal_input(tmp_path: Path) -> None:
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    projection.save(fixture_record())

    assert projection.search("%' OR 1=1 --") == ()
    with pytest.raises(ValueError, match="unknown epistemic category"):
        projection.search("sample", category="not_a_category")


def test_reindexing_one_record_replaces_stale_items_and_relationships(tmp_path: Path) -> None:
    record = fixture_record()
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    projection.save(record)
    reduced = record.model_copy(
        update={
            "epistemic_items": record.epistemic_items[:2],
            "skeptical_challenges": (),
        }
    )

    projection.save(reduced)

    assert projection.load_record(record.id) == reduced
    assert projection.search("nonzero") == ()
    assert projection.relationships(record.id) == ()


def test_unit_of_work_updates_both_stores_or_restores_previous_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "investigations")
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    unit_of_work = InvestigationUnitOfWork(markdown, projection)
    original = fixture_record()
    unit_of_work.save(original)
    changed = original.model_copy(update={"seed": "A changed question."})

    def fail_projection_save(record: object) -> None:
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(projection, "save", fail_projection_save)

    with pytest.raises(RuntimeError, match="simulated projection failure"):
        unit_of_work.save(changed)

    assert markdown.load(original.id) == original
    assert SQLiteProjection(tmp_path / "forge.sqlite3").load_record(original.id) == original


def test_unit_of_work_removes_new_markdown_when_initial_projection_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "investigations")
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    unit_of_work = InvestigationUnitOfWork(markdown, projection)
    record = fixture_record()

    def fail_projection_save(record: object) -> None:
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(projection, "save", fail_projection_save)

    with pytest.raises(RuntimeError, match="simulated projection failure"):
        unit_of_work.save(record)

    assert not (tmp_path / "investigations" / f"{record.id}.md").exists()


def test_version_one_projection_migrates_relationship_targets(tmp_path: Path) -> None:
    database_path = tmp_path / "forge.sqlite3"
    record = fixture_record()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_info (version INTEGER NOT NULL);
            INSERT INTO schema_info (version) VALUES (1);
            CREATE TABLE investigations (
                id TEXT PRIMARY KEY,
                seed TEXT NOT NULL,
                selected_focus TEXT,
                depth TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                record_json TEXT NOT NULL
            );
            CREATE TABLE epistemic_items (
                investigation_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                category TEXT NOT NULL,
                subtype TEXT,
                statement TEXT NOT NULL,
                confidence_level TEXT NOT NULL,
                provenance_origin TEXT NOT NULL,
                PRIMARY KEY (investigation_id, item_id)
            );
            CREATE TABLE relationships (
                investigation_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                relation_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                PRIMARY KEY (investigation_id, source_id, relation_kind, target_id)
            );
            """
        )
        connection.execute(
            """
            INSERT INTO investigations (
                id, seed, selected_focus, depth, stage, status,
                created_at, updated_at, record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.seed,
                record.selected_focus,
                record.workflow.depth.value,
                record.workflow.stage.value,
                record.workflow.status.value,
                record.workflow.created_at.isoformat(),
                record.workflow.updated_at.isoformat(),
                record.model_dump_json(),
            ),
        )
        for item_id in ("epi_nonzero_mass", "epi_mass_reading"):
            connection.execute(
                """
                INSERT INTO epistemic_items (
                    investigation_id, item_id, category, subtype, statement,
                    confidence_level, provenance_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (record.id, item_id, "derived_claim", None, item_id, "medium", "legacy"),
            )
        connection.execute(
            """
            INSERT INTO relationships (
                investigation_id, source_id, relation_kind, target_id
            ) VALUES (?, ?, ?, ?)
            """,
            (record.id, "epi_nonzero_mass", "supports", "epi_mass_reading"),
        )

    projection = SQLiteProjection(database_path)

    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT version FROM schema_info").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(relationships)").fetchall()
        }
    assert version == 2
    assert "target_investigation_id" in columns
    assert projection.relationships(record.id) == (
        ("epi_nonzero_mass", "supports", record.id, "epi_mass_reading"),
    )

    projection.save(record)
    assert set(projection.relationships(record.id)) == {
        ("epi_nonzero_mass", "depends_on", record.id, "epi_closed_system"),
        ("epi_nonzero_mass", "depends_on", record.id, "epi_mass_reading"),
        ("epi_nonzero_mass", "supports", record.id, "epi_mass_reading"),
        ("epi_temperature_connection", "based_on", record.id, "epi_mass_reading"),
    }


def test_failed_version_one_migration_is_atomic(tmp_path: Path) -> None:
    database_path = tmp_path / "failed-v1.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_info (version INTEGER NOT NULL);
            INSERT INTO schema_info (version) VALUES (1);
            CREATE TABLE relationships (
                investigation_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                relation_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                PRIMARY KEY (investigation_id, source_id, relation_kind, target_id)
            );
            INSERT INTO relationships (
                investigation_id, source_id, relation_kind, target_id
            ) VALUES ('inv_orphan', 'epi_missing', 'supports', 'epi_target');
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        SQLiteProjection(database_path)

    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT version FROM schema_info").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(relationships)").fetchall()
        }
        legacy_row = connection.execute(
            "SELECT investigation_id, source_id, relation_kind, target_id FROM relationships"
        ).fetchone()
    assert version == 1
    assert "target_investigation_id" not in columns
    assert legacy_row == ("inv_orphan", "epi_missing", "supports", "epi_target")
