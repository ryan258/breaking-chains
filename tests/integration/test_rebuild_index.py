import sqlite3
from pathlib import Path

import pytest

from forge.domain.epistemics import EpistemicLink, LinkKind
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection


def fixture_record():
    fixture_root = Path(__file__).parents[1] / "fixtures"
    return MarkdownInvestigationRepository(fixture_root).load("inv_mass_question")


def test_deleted_sqlite_index_rebuilds_from_canonical_markdown(tmp_path: Path) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "investigations")
    first = fixture_record()
    second = first.model_copy(
        update={
            "id": "inv_second_question",
            "seed": "Could temperature alter repeated readings?",
        }
    )
    cross_link = EpistemicLink(
        kind=LinkKind.CONNECTS,
        target_id="epi_closed_system",
        target_investigation_id=first.id,
    )
    linked_item = second.epistemic_items[-1].model_copy(update={"links": (cross_link,)})
    second = second.model_copy(
        update={"epistemic_items": (*second.epistemic_items[:-1], linked_item)}
    )
    markdown.save(first)
    markdown.save(second)
    database_path = tmp_path / "forge.sqlite3"
    projection = SQLiteProjection(database_path)
    projection.save(first)
    database_path.unlink()

    rebuilt = SQLiteProjection(database_path)
    rebuilt.rebuild(markdown.list_records())

    assert rebuilt.count_investigations() == 2
    assert rebuilt.load_record(first.id) == first
    assert rebuilt.load_record(second.id) == second
    assert len(rebuilt.search("temperature", category="exploratory_item")) == 2
    assert set(rebuilt.relationships(second.id)) == {
        ("epi_nonzero_mass", "depends_on", second.id, "epi_closed_system"),
        ("epi_nonzero_mass", "depends_on", second.id, "epi_mass_reading"),
        ("epi_nonzero_mass", "supports", second.id, "epi_mass_reading"),
        ("epi_temperature_connection", "based_on", second.id, "epi_mass_reading"),
        ("epi_temperature_connection", "connects", first.id, "epi_closed_system"),
    }


def test_failed_rebuild_leaves_previous_projection_intact(tmp_path: Path) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "investigations")
    record = fixture_record()
    markdown.save(record)
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    projection.save(record)
    replacement = record.model_copy(update={"id": "inv_replacement"})
    with sqlite3.connect(tmp_path / "forge.sqlite3") as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_replacement
            BEFORE INSERT ON investigations
            WHEN NEW.id = 'inv_replacement'
            BEGIN
                SELECT RAISE(ABORT, 'simulated mid-rebuild failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="simulated mid-rebuild failure"):
        projection.rebuild((replacement,))

    assert projection.count_investigations() == 1
    assert projection.load_record(record.id) == record
