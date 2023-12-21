from dataclasses import dataclass, field


@dataclass(order=True, frozen=True)
class ChapterInfo:
    title: str
    """Chapter title"""
    chapter_number: int
    """Released chapter number"""
    data_episode_no: int
    """Chapter number referenced by webtoon server"""
    content_url: str
    """Chapter URL"""

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "sort_index", self.chapter_number)
