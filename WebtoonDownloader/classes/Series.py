from dataclasses import dataclass, field
@dataclass(order=True)
class Series:
    series_url: str
    series_title: str = ""
    viewer_url: str = ""

@dataclass(order=True, frozen=True)
class ChapterInfo:
    sort_index: int = field(init=False, repr=False)
    title: str
    chapter_number: int #released chapter number
    data_episode_no: int #chapter number referenced by webtoon server
    content_url: str
    def __post_init__(self):
        object.__setattr__(self, 'sort_index', self.chapter_number)
