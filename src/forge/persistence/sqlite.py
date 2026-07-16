"""Rebuildable SQLite projection for workflow state and epistemic search."""

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from forge.domain.epistemics import DerivedClaim, Evidence, ExploratoryItem, Premise
from forge.persistence.markdown import RecordFormatError
from forge.persistence.metadata import InvestigationRecord

_SCHEMA_VERSION = 2
_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS investigations (
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

CREATE TABLE IF NOT EXISTS epistemic_items (
    investigation_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    category TEXT NOT NULL,
    subtype TEXT,
    statement TEXT NOT NULL,
    confidence_level TEXT NOT NULL,
    provenance_origin TEXT NOT NULL,
    PRIMARY KEY (investigation_id, item_id),
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
    investigation_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relation_kind TEXT NOT NULL,
    target_investigation_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY (
        investigation_id, source_id, relation_kind, target_investigation_id, target_id
    ),
    FOREIGN KEY (investigation_id, source_id)
        REFERENCES epistemic_items(investigation_id, item_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_category
    ON epistemic_items(category);
CREATE INDEX IF NOT EXISTS idx_items_statement
    ON epistemic_items(statement);
CREATE INDEX IF NOT EXISTS idx_relationship_target
    ON relationships(target_id);
"""

_CATEGORIES = frozenset({"premise", "evidence", "derived_claim", "exploratory_item"})

_MIGRATE_V1_TO_V2 = """
BEGIN IMMEDIATE;

DROP INDEX IF EXISTS idx_relationship_target;
ALTER TABLE relationships RENAME TO relationships_v1;

CREATE TABLE relationships (
    investigation_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relation_kind TEXT NOT NULL,
    target_investigation_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY (
        investigation_id, source_id, relation_kind, target_investigation_id, target_id
    ),
    FOREIGN KEY (investigation_id, source_id)
        REFERENCES epistemic_items(investigation_id, item_id) ON DELETE CASCADE
);

INSERT INTO relationships (
    investigation_id, source_id, relation_kind, target_investigation_id, target_id
)
SELECT investigation_id, source_id, relation_kind, investigation_id, target_id
FROM relationships_v1;

DROP TABLE relationships_v1;
CREATE INDEX idx_relationship_target ON relationships(target_id);
UPDATE schema_info SET version = 2;

COMMIT;
"""


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One bounded search result from the disposable projection."""

    investigation_id: str
    item_id: str
    category: str
    subtype: str | None
    statement: str


class ProjectionRecordNotFound(LookupError):
    """No indexed investigation has the requested identifier."""


class SQLiteProjection:
    """Transactional, normalized projection that can be rebuilt from Markdown."""

    def __init__(self, path: Path) -> None:
        self.path = path
        parent_existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not parent_existed:
            os.chmod(self.path.parent, 0o700)
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except OSError as error:
            raise ValueError("unable to open SQLite projection safely") from error
        try:
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            row = connection.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_info (version) VALUES (?)",
                    (_SCHEMA_VERSION,),
                )
            elif row[0] == 1:
                connection.executescript(_MIGRATE_V1_TO_V2)
            elif row[0] != _SCHEMA_VERSION:
                raise RuntimeError("unsupported SQLite projection schema")

    def save(self, record: InvestigationRecord) -> None:
        """Replace one investigation projection in a single SQL transaction."""

        validated = _validate_record(record)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _replace_record(connection, validated)

    def rebuild(self, records: tuple[InvestigationRecord, ...]) -> None:
        """Replace every indexed record transactionally from canonical inputs."""

        validated_records = tuple(_validate_record(record) for record in records)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM investigations")
            for record in validated_records:
                _replace_record(connection, record)

    def load_record(self, investigation_id: str) -> InvestigationRecord:
        """Load resumable state from the projection through domain validation."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM investigations WHERE id = ?",
                (investigation_id,),
            ).fetchone()
        if row is None:
            raise ProjectionRecordNotFound(investigation_id)
        try:
            return InvestigationRecord.model_validate_json(row[0])
        except ValidationError:
            raise RecordFormatError("indexed investigation record is invalid") from None

    def count_investigations(self) -> int:
        """Return the number of canonical records represented in the index."""

        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM investigations").fetchone()
        return int(row[0])

    def relationships(self, investigation_id: str) -> tuple[tuple[str, str, str, str], ...]:
        """Return every explicit, dependency, and basis relationship."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_id, relation_kind, target_investigation_id, target_id
                FROM relationships
                WHERE investigation_id = ?
                ORDER BY source_id, relation_kind, target_investigation_id, target_id
                """,
                (investigation_id,),
            ).fetchall()
        return tuple((row[0], row[1], row[2], row[3]) for row in rows)

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[SearchHit, ...]:
        """Search epistemic statements with literal, parameterized input."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("search query must not be blank")
        if category is not None and category not in _CATEGORIES:
            raise ValueError("unknown epistemic category")
        if not 1 <= limit <= 100:
            raise ValueError("search limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("search offset must not be negative")

        where = "statement LIKE ? ESCAPE '\\' COLLATE NOCASE"
        parameters: list[str | int] = [f"%{_escape_like(normalized_query)}%"]
        if category is not None:
            where += " AND category = ?"
            parameters.append(category)
        parameters.extend((limit, offset))

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT investigation_id, item_id, category, subtype, statement
                FROM epistemic_items
                WHERE {where}
                ORDER BY investigation_id, item_id
                LIMIT ? OFFSET ?
                """,
                parameters,
            ).fetchall()
        return tuple(SearchHit(*row) for row in rows)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _validate_record(record: InvestigationRecord) -> InvestigationRecord:
    try:
        return InvestigationRecord.model_validate(record.model_dump(mode="python"))
    except ValidationError:
        raise RecordFormatError("invalid investigation record") from None


def _replace_record(connection: sqlite3.Connection, record: InvestigationRecord) -> None:
    connection.execute(
        """
        INSERT INTO investigations (
            id, seed, selected_focus, depth, stage, status, created_at, updated_at, record_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            seed = excluded.seed,
            selected_focus = excluded.selected_focus,
            depth = excluded.depth,
            stage = excluded.stage,
            status = excluded.status,
            created_at = excluded.created_at,
            updated_at = excluded.updated_at,
            record_json = excluded.record_json
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
    connection.execute("DELETE FROM epistemic_items WHERE investigation_id = ?", (record.id,))

    for item in record.epistemic_items:
        subtype, provenance = _item_projection(item)
        connection.execute(
            """
            INSERT INTO epistemic_items (
                investigation_id, item_id, category, subtype, statement,
                confidence_level, provenance_origin
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                item.id,
                item.category,
                subtype,
                item.statement,
                item.uncertainty.level.value,
                provenance,
            ),
        )
        relationships = [
            (link.kind.value, link.target_investigation_id or record.id, link.target_id)
            for link in item.links
        ]
        if isinstance(item, DerivedClaim):
            relationships.extend(
                ("depends_on", record.id, dependency) for dependency in item.dependencies
            )
        elif isinstance(item, ExploratoryItem):
            relationships.extend(("based_on", record.id, basis) for basis in item.based_on)
        for relation_kind, target_investigation_id, target_id in relationships:
            connection.execute(
                """
                INSERT INTO relationships (
                    investigation_id, source_id, relation_kind, target_investigation_id, target_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (record.id, item.id, relation_kind, target_investigation_id, target_id),
            )


def _item_projection(item: object) -> tuple[str | None, str]:
    if isinstance(item, Premise):
        return None, item.origin
    if isinstance(item, Evidence):
        return item.details.evidence_type, item.provenance.origin
    if isinstance(item, ExploratoryItem):
        return item.exploratory_type.value, item.provenance.origin
    if isinstance(item, DerivedClaim):
        return None, item.provenance.origin
    raise TypeError("unsupported epistemic item")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


__all__ = [
    "ProjectionRecordNotFound",
    "SQLiteProjection",
    "SearchHit",
]
