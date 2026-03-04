from dataclasses import dataclass

import pytest
from bs4 import BeautifulSoup

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.extractor import WebtoonMainPageExtractor, WebtoonViewerPageExtractor


@dataclass
class WebtoonTestCase:
    test_id: str
    url: str
    expected_title: str
    expected_summary: str


main_page_test_cases = [
    WebtoonTestCase(
        "RegularWebtoon#1 (TowerOfGod)",
        "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
        "Tower of God",
        "What do you desire? Money and wealth? Honor and pride? Authority and power? Revenge? Or something that transcends them all? Whatever you desire—it's here.",
    ),
    WebtoonTestCase(
        "WebtoonFrench (TowerOfGod)",
        "https://www.webtoons.com/fr/fantasy/tower-of-god/list?title_no=1832",
        "Tower of God",
        "“Que désirez-vous? La richesse? La gloire? Le pouvoir? La vengeance? Ou une chose qui surpasse toutes les autres ? Quel que soit votre désir, il se trouve ici !”",
    ),
    WebtoonTestCase(
        "RegularWebtoon#2 (DICE)",
        "https://www.webtoons.com/en/fantasy/dice/list?title_no=64",
        "DICE",
        "Whether it's appearance, grades, or social life, Dongtae's at the bottom of the barrel. When popular transfer student Taebin gives him an opportunity to change all of that, Dongtae heads down a path to make things right. This is the world of DICE, where a single roll can change your fate.",
    ),
    WebtoonTestCase(
        "WebtoonMultiAuthors (PurpleHyacinth)",
        "https://www.webtoons.com/en/mystery/purple-hyacinth/list?title_no=1621",
        "Purple Hyacinth",
        "Her ability to detect lies has made her an outstanding officer of the law – despite being haunted by her inability to save the ones she loved from a gruesome fate many years ago. Now, she uses her powerful gift to defend the defenseless at any cost – even if it means teaming up with a deadly assassin to fight evil in a world gone mad.",
    ),
    WebtoonTestCase(
        "CanvasWebtoon#1 (Swords)",
        "https://www.webtoons.com/en/canvas/swords/list?title_no=198852",
        "SWORDS: The Webcomic",
        "In a world where everything is a sword, only the sharpest heroes survive! These are the tales of many different adventurers, living their lives in a realm corrupted by Seven Demon Swords.",
    ),
    WebtoonTestCase(
        "CanvasWebtoonMultiAuthors (Crawling Dreams)",
        "https://www.webtoons.com/en/canvas/crawling-dreams/list?title_no=141539",
        "Crawling Dreams",
        "Nyarla and Ghast are living in a trendy city by the sea, that seems to be hiding some disturbing secrets. --- Art by Osiimi & Minster, and Story by Merryweather",
    ),
]


@pytest.mark.network
@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", main_page_test_cases, ids=lambda tc: tc.test_id)
async def test_webtoon_main_page_extractor(test_case: WebtoonTestCase) -> None:
    async with WebtoonHttpClient() as client:
        resp = await client.get(test_case.url)

    extractor = WebtoonMainPageExtractor(resp.text)
    assert extractor.series_title.strip() == test_case.expected_title
    assert extractor.series_summary.strip() == test_case.expected_summary


@dataclass
class ViewerTestCase:
    test_id: str
    url: str
    expected_notes: str
    expected_img_count: int


viewer_test_cases = [
    ViewerTestCase(
        test_id="ViewerRegularEN#TowerOfGodEp234",
        url="https://www.webtoons.com/en/fantasy/tower-of-god/season-3-ep-234/viewer?title_no=95&episode_no=652",
        expected_notes="",
        expected_img_count=119,
    ),
    ViewerTestCase(
        test_id="ViewerRegularFR#TowerOfGodEp234",
        url="https://www.webtoons.com/fr/fantasy/tower-of-god/saison-3-ep-234/viewer?title_no=1832&episode_no=651",
        expected_notes="",
        expected_img_count=137,
    ),
    ViewerTestCase(
        test_id="ViewerCanvasEN#SwordsEp1",
        url="https://www.webtoons.com/en/canvas/swords-the-webcomic/swords-i/viewer?title_no=198852&episode_no=1",
        expected_notes="Ask not for who the Bread swings, its swings for thee.",
        expected_img_count=8,
    ),
]


@pytest.mark.network
@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", viewer_test_cases, ids=lambda tc: tc.test_id)
async def test_webtoon_viewer_page_extractor(test_case: ViewerTestCase) -> None:
    async with WebtoonHttpClient() as client:
        resp = await client.get(test_case.url)

    extractor = WebtoonViewerPageExtractor(resp.text)

    assert extractor.chapter_notes.strip() == test_case.expected_notes
    assert len(extractor.img_urls) == test_case.expected_img_count


def test_get_author_from_meta_tag() -> None:
    soup = BeautifulSoup(
        """
        <html>
          <head>
            <meta property='com-linewebtoon:webtoon:author' content='SIU' />
          </head>
          <body></body>
        </html>
        """,
        "lxml",
    )
    extractor = WebtoonMainPageExtractor(soup)
    assert extractor.author == "SIU"


def test_get_author_from_author_area_fallback() -> None:
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div class='author_area'> Osiimi, Merryweather <button>Follow</button></div>
          </body>
        </html>
        """,
        "lxml",
    )
    extractor = WebtoonMainPageExtractor(soup)
    assert extractor.author == "Osiimi, Merryweather"


def test_get_author_missing_returns_none_with_debug_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    extractor = WebtoonMainPageExtractor(BeautifulSoup("<html><body></body></html>", "lxml"))
    assert extractor.author is None
    assert "Author not found in known selectors" in caplog.text


def test_get_genre_from_heading() -> None:
    extractor = WebtoonMainPageExtractor(BeautifulSoup("<h2 class='genre g_fantasy'>Fantasy</h2>", "lxml"))
    assert extractor.genre == "Fantasy"


def test_get_genre_missing_returns_none_with_debug_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    extractor = WebtoonMainPageExtractor(BeautifulSoup("<html><body></body></html>", "lxml"))
    assert extractor.genre is None
    assert "Genre not found in known selectors" in caplog.text
