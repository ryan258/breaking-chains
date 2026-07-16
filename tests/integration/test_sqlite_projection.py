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
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")

    projection.save(record)

    assert projection.load_record(record.id) == record
    assert projection.count_investigations() == 1
    assert set(projection.relationships(record.id)) == {
        ("epi_nonzero_mass", "depends_on", "epi_closed_system"),
        ("epi_nonzero_mass", "depends_on", "epi_mass_reading"),
        ("epi_nonzero_mass", "supports", "epi_mass_reading"),
        ("epi_temperature_connection", "based_on", "epi_mass_reading"),
    }


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
