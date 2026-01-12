from __future__ import annotations

import os
from pathlib import Path


def default_db_path() -> Path:
    """
    Default per-user database:
      ~/.flowtask/flowtask.db

    Override with FLOWTASK_DB env var or --db CLI option.
    """
    env = os.getenv("FLOWTASK_DB")
    if env:
        return Path(env).expanduser().resolve()

    return (Path.home() / ".flowtask" / "flowtask.db").resolve()