from dataclasses import dataclass, field


@dataclass(order=True, frozen=True)
class ChapterInfo:
    """
    An immutable object representing a chapter of a webtoon. It supports ordering based on the chapter number.

    Attributes:
        chapter_number  : The released chapter number, used for user-facing purposes.
        viewer_url      : The URL where the chapter content can be accessed.
        data_episode_no : An internal identifier for the chapter, as used by the webtoon viewer.
        title           : The title of the chapter.
    """

    number: int
    viewer_url: str
    data_episode_no: int
    title: str
    series_title: str
    total_chapters: int

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sort_index", self.number)


@dataclass(order=True, frozen=True)
class PageInfo:
    """
    An immutable object representing a webtoon image page. It supports ordering based on the page number.

    Attributes:
        page_number     : The page number of the chapter.
        content_url     : The direct link to the img ressource.
        total_pages     : Total number of pages in the chapter.
    """

    page_number: int
    url: str
    total_pages: int
    chapter_info: ChapterInfo

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sort_index", self.page_number)
