from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

DownloadResult: TypeAlias = str | Path
"""Type representation of the download result as either a string or Path object."""
