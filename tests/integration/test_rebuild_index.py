from pathlib import Path

import pytest

from forge.persistence.markdown import MarkdownInvestigationRepository, RecordFormatError
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
        ("epi_nonzero_mass", "depends_on", "epi_closed_system"),
        ("epi_nonzero_mass", "depends_on", "epi_mass_reading"),
        ("epi_nonzero_mass", "supports", "epi_mass_reading"),
        ("epi_temperature_connection", "based_on", "epi_mass_reading"),
    }


def test_failed_rebuild_leaves_previous_projection_intact(tmp_path: Path) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "investigations")
    record = fixture_record()
    markdown.save(record)
    projection = SQLiteProjection(tmp_path / "forge.sqlite3")
    projection.save(record)
    invalid_copy = record.model_copy(update={"epistemic_items": (record.epistemic_items[0],) * 2})

    with pytest.raises(RecordFormatError, match="invalid investigation record"):
        projection.rebuild((invalid_copy,))

    assert projection.count_investigations() == 1
    assert projection.load_record(record.id) == record
