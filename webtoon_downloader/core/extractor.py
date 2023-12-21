from typing import Union

from bs4 import BeautifulSoup


class InvalidHTMLObject(TypeError):
    """Exception raised when variable is neither a string nor a BeautifulSoup object."""

    def __str__(self):
        return "Variable passed is neither a string nor a BeautifulSoup object"


def get_series_title(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the full title series from the html of the scraped url.

    Arguments:
    ----------
    series_url  : url of the series to scrap from the webtoons.com website \
                  series title are grabbed differently for webtoons of the challenge category
    html        : the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object

    Returns:
    ----------
        The full title of the series.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    series_title = _html.find(class_="subj").get_text(separator=" ").replace("\n", "").replace("\t", "")
    return series_title


def get_series_summary(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the series summary from the html of the series overview page.

    Arguments:
    ----------

    html : the html body of the scraped series overview page, passed either as a raw
           string or a bs4.BeautifulSoup object

    Returns:
    --------
        The series summary
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    return _html.find(class_="summary").get_text(separator=" ").replace("\n", "").replace("\t", "")


def get_chapter_title(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the chapter title from the html of the chapter.

    Arguments:
    ----------

    html : the html body of the scraped chapter, passed either as a raw string or
           a bs4.BeautifulSoup object

    Returns:
    --------
        The chapter title
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    return _html.find("h1").get_text().strip()


def get_chapter_notes(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the chapter author notes from the html of the chapter.

    Arguments:
    ----------

    html : the html body of the scraped chapter, passed either as a raw string or
           a bs4.BeautifulSoup object

    Returns:
    --------
        The chapter notes or None if not available
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    node = _html.find(class_="author_text")
    if node is None:
        return None
    else:
        return node.get_text().strip().replace("\r\n", "\n")


def extract_img_urls(html: Union[str, BeautifulSoup]) -> list:
    """
    Extract the image URLs from the chapters HTML document.

    Arguments:
    ----------
    html : the html body of the chapter, passed either as a raw string or a bs4.BeautifulSoup object

    Returns:
    --------
    (list[str]): list of all image urls extracted from the chapter.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html, "lxml")
    return [url["data-url"] for url in _html.find("div", class_="viewer_img _img_viewer_area").find_all("img")]


def get_chapter_viewer_url(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the url of the webtoon chapter reader related to the series given in the series url.

    Arguments:
    ----------
    html : str | BeautifulSoup
        the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object

    Returns:
    ----------
    (str): chapter reader url.
    """
    if isinstance(html, str):
        return BeautifulSoup(html).find("li", attrs={"data-episode-no": True}).find("a")["href"].split("&")[0]

    if isinstance(html, BeautifulSoup):
        return html.find("li", attrs={"data-episode-no": True}).find("a")["href"].split("&")[0]

    raise InvalidHTMLObject()
