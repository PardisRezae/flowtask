from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    description: str
    priority: int
    due: Optional[date]
    status: str  # "todo" | "done"
    tags: str
    created_at: datetime
    updated_at: datetime