"""Stable identifiers for domain records."""

from typing import Annotated
from uuid import uuid4

from pydantic import StringConstraints

EpistemicItemId = Annotated[
    str,
    StringConstraints(pattern=r"^epi_[a-z0-9][a-z0-9_-]{2,63}$"),
]
InvestigationId = Annotated[
    str,
    StringConstraints(pattern=r"^inv_[a-z0-9][a-z0-9_-]{0,59}$"),
]
CallId = Annotated[
    str,
    StringConstraints(pattern=r"^call_[a-z0-9][a-z0-9_-]{0,59}$"),
]


def new_epistemic_item_id() -> str:
    """Create a stable opaque identifier for an epistemic item."""

    return f"epi_{uuid4().hex}"


def new_call_id() -> str:
    """Create a safe opaque identifier for a model call."""

    return f"call_{uuid4().hex}"
