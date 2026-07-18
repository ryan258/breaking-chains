"""Coordinated canonical and projection persistence."""

from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.metadata import InvestigationRecord
from forge.persistence.sqlite import SQLiteProjection


class InvestigationUnitOfWork:
    """Canonical Markdown always wins; the projection is a rebuildable index."""

    def __init__(
        self,
        markdown: MarkdownInvestigationRepository,
        projection: SQLiteProjection,
    ) -> None:
        self.markdown = markdown
        self.projection = projection

    def save(self, record: InvestigationRecord) -> None:
        """Persist canonical Markdown, then refresh the disposable projection."""

        self.markdown.save(record)
        try:
            self.projection.save(record)
        except Exception:
            # The projection is derived data: never sacrifice the canonical
            # record to keep it in lockstep. Restore it from Markdown instead.
            self.projection.rebuild(self.markdown.list_records())

    def load(self, investigation_id: str) -> InvestigationRecord:
        """Load canonical working state for orchestration or resumption."""

        return self.markdown.load(investigation_id)

    def exists(self, investigation_id: str) -> bool:
        """Return whether canonical working state already exists."""

        return self.markdown.exists(investigation_id)


__all__ = ["InvestigationUnitOfWork"]
