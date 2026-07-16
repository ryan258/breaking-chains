"""Coordinated canonical and projection persistence."""

from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.metadata import InvestigationRecord
from forge.persistence.sqlite import SQLiteProjection


class PersistenceConsistencyError(RuntimeError):
    """A failed projection could not be compensated in canonical storage."""


class InvestigationUnitOfWork:
    """Keep canonical Markdown and its disposable projection aligned."""

    def __init__(
        self,
        markdown: MarkdownInvestigationRepository,
        projection: SQLiteProjection,
    ) -> None:
        self.markdown = markdown
        self.projection = projection

    def save(self, record: InvestigationRecord) -> None:
        """Save both stores or restore the prior canonical record."""

        previous = self.markdown.load(record.id) if self.markdown.exists(record.id) else None
        self.markdown.save(record)
        try:
            self.projection.save(record)
        except Exception:
            try:
                if previous is None:
                    self.markdown.delete(record.id)
                else:
                    self.markdown.save(previous)
            except Exception as rollback_error:
                raise PersistenceConsistencyError(
                    "projection save failed and canonical rollback also failed"
                ) from rollback_error
            raise

    def load(self, investigation_id: str) -> InvestigationRecord:
        """Load canonical working state for orchestration or resumption."""

        return self.markdown.load(investigation_id)


__all__ = ["InvestigationUnitOfWork", "PersistenceConsistencyError"]
