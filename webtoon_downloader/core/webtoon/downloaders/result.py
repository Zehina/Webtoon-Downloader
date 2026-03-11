from __future__ import annotations

from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

DownloadResult: TypeAlias = Union[str, Path]
"""Type representation of the download result as either a string or Path object."""
