from dataclasses import dataclass
@dataclass(order=True)
class Series:
    series_url: str
    series_title: str = ""
    viewer_url: str = ""
