from dataclasses import dataclass

@dataclass(order=True, frozen=True)
class DownloadSettings:
    start: int
    end: int
    dest: str
    max_concurrent: int
    images_format: str = 'jpg'
    latest: bool = False
    separate: bool = False
    compress: bool = False