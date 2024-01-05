from __future__ import annotations

from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

DownloadResult: TypeAlias = Union[str, Path]
"""Type reprensentation the download result which can either be represented as a string or Path object"""
