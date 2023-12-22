from dataclasses import dataclass, field


@dataclass(order=True, frozen=True)
class ChapterInfo:
    """
    A data class representing a chapter of a webtoon. It supports ordering based on the chapter number.

    Attributes:
        title           : The title of the chapter.
        chapter_number  : The released chapter number, used for user-facing purposes.
        data_episode_no : An internal identifier for the chapter, as used by the webtoon viewer.
        content_url     : The URL where the chapter content can be accessed.
    """

    title: str
    chapter_number: int
    data_episode_no: int
    content_url: str

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sort_index", self.chapter_number)
