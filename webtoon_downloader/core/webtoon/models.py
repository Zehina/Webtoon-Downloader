from dataclasses import dataclass, field


@dataclass(order=True, frozen=True)
class ChapterInfo:
    """
    An immutable object representing a chapter of a webtoon. It supports ordering based on the chapter number.

    Attributes:
        chapter_number  : The released chapter number, used for user-facing purposes.
        content_url     : The URL where the chapter content can be accessed.
        data_episode_no : An internal identifier for the chapter, as used by the webtoon viewer.
        title           : The title of the chapter.
    """

    chapter_number: int
    content_url: str
    data_episode_no: int
    title: str

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sort_index", self.chapter_number)
