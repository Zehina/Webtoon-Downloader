from dataclasses import dataclass

import httpx
import pytest

from webtoon_downloader.core.client import WebtoonClient
from webtoon_downloader.core.extractor import WebtoonMainPageExtractor


@dataclass
class WebtoonTestCase:
    test_id: str
    url: str
    expected_title: str
    expected_summary: str
    expected_viewer_url: str


test_cases = [
    WebtoonTestCase(
        "RegularWebtoon#1 (TowerOfGod)",
        "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
        "Tower of God",
        "What do you desire? Money and wealth? Honor and pride? Authority and power? Revenge? Or something that transcends them all? Whatever you desire—it's here.",
        "https://www.webtoons.com/en/fantasy/tower-of-god/season-1-ep-0/viewer?title_no=95",
    ),
    WebtoonTestCase(
        "WebtoonFrench (TowerOfGod)",
        "https://www.webtoons.com/fr/fantasy/tower-of-god/list?title_no=1832",
        "Tower of God",
        "“Que désirez-vous? La richesse? La gloire? Le pouvoir? La vengeance? Ou une chose qui surpasse toutes les autres ? Quel que soit votre désir, il se trouve ici !”",
        "https://www.webtoons.com/fr/fantasy/tower-of-god/saison-1-prologue/viewer?title_no=1832",
    ),
    WebtoonTestCase(
        "RegularWebtoon#2 (DICE)",
        "https://www.webtoons.com/en/fantasy/dice/list?title_no=64",
        "DICE",
        "Whether it's appearance, grades, or social life, Dongtae's at the bottom of the barrel. When popular transfer student Taebin gives him an opportunity to change all of that, Dongtae heads down a path to make things right. This is the world of DICE, where a single roll can change your fate.",
        "https://www.webtoons.com/en/fantasy/dice/ep-0/viewer?title_no=64",
    ),
    WebtoonTestCase(
        "WebtoonMultiAuthors (PurpleHyacinth)",
        "https://www.webtoons.com/en/mystery/purple-hyacinth/list?title_no=1621",
        "Purple Hyacinth",
        "Her ability to detect lies has made her an outstanding officer of the law – despite being haunted by her inability to save the ones she loved from a gruesome fate many years ago. Now, she uses her powerful gift to defend the defenseless at any cost – even if it means teaming up with a deadly assassin to fight evil in a world gone mad.",
        "https://www.webtoons.com/en/mystery/purple-hyacinth/ep-0-prologue/viewer?title_no=1621",
    ),
    WebtoonTestCase(
        "CanvasWebtoon#1 (Swords)",
        "https://www.webtoons.com/en/canvas/swords/list?title_no=198852",
        "Swords",
        "In a world where everything is a sword, only the sharpest heroes survive! These are the tales of many different adventurers, living their lives in a realm corrupted by Seven Demon Swords.",
        "https://www.webtoons.com/en/canvas/swords/swords-i/viewer?title_no=198852",
    ),
    WebtoonTestCase(
        "CanvasWebtoonMultiAuthors (Crawling Dreams)",
        "https://www.webtoons.com/en/canvas/crawling-dreams/list?title_no=141539",
        "Crawling Dreams",
        "Nyarla and Ghast are living in a trendy city by the sea, that seems to be hiding some disturbing secrets. --- Art by Osiimi & Minster, and Story by Merryweather",
        "https://www.webtoons.com/en/canvas/crawling-dreams/ep-1-nyarla-ghast/viewer?title_no=141539",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
async def test_webtoon_main_page_extractor(test_case: WebtoonTestCase):
    async with WebtoonClient(http_client=httpx.AsyncClient(http2=True)) as client:
        resp = await client.get(test_case.url)

    extractor = WebtoonMainPageExtractor(resp.text)
    assert extractor.get_series_title().strip() == test_case.expected_title
    assert extractor.get_series_summary().strip() == test_case.expected_summary
    assert extractor.get_chapter_viewer_url() == test_case.expected_viewer_url
