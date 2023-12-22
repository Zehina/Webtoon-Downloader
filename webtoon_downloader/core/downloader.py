import itertools
import logging
import math
import os
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from threading import Event
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import requests
import rich
from bs4 import BeautifulSoup
from rich.progress import Progress, TaskID

from webtoon_downloader.core.extractor import (
    WebtoonMainPageExtractor,
    WebtoonViewerPageExtractor,
)
from webtoon_downloader.core.models import ChapterInfo
from webtoon_downloader.core.utils import (
    TextExporter,
    ThreadPoolExecutorWithQueueSizeLimit,
    download_image,
    get_chapter_dir,
    slugify_file_name,
)

log = logging.getLogger(__name__)

N_CONCURRENT_CHAPTERS_DOWNLOAD = 10
USER_AGENT = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/92.0.4515.107 Safari/537.36"
    )
    if os.name == "nt"
    else ("Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)" "Gecko/20100101 Firefox/75.0")
)
headers = {
    "dnt": "1",
    "user-agent": USER_AGENT,
    "accept-language": "en-US,en;q=0.9",
}


def get_first_chapter_episode_no(session: requests.Session, series_url: str) -> int:
    """
    Fetches the 'episode_no' field that is used in a Webtoon's viewer. Most series should start with episode 1
    but some start at 2, and others might even be 80+.

    Args:
        session: The session with which to send HTTP requests.
        series_url: The URL of the Webtoon series.

    Returns:
       The episode number of the first chapter of the Webtoon series.
    """

    try:
        # First attempt to fetch the episode_no
        soup = BeautifulSoup(session.get(series_url).text, "html.parser")
        _tag = soup.find("a", id="_btnEpisode")
        if not _tag:
            return -1

        return int(parse_qs(urlparse(_tag["href"]).query)["episode_no"][0])
    except (TypeError, KeyError):
        # If the second attempt fails, try to get the first episode from the list
        soup = BeautifulSoup(session.get(f"{series_url}&page=9999").text, "html.parser")
        return min(int(episode["data-episode-no"]) for episode in soup.find_all("li", {"class": "_episodeItem"}))


def get_chapters_details(
    session: requests.Session,
    viewer_url: str,
    series_url: str,
    start_chapter: int = 1,
    end_chapter: Optional[int] = None,
) -> List[ChapterInfo]:
    """
    Extracts data about all chapters of the series.

    Arguments:
    ----------
    session: requests.session
        the requests session object for persistent parameters.

    viewer_url: str
        chapter reader url of the series.

    start_chapter: int
        starting range of chapters to download.
        (default: 1)

    end_chapter: int
        end range of chapter to download, inclusive of this chapter number.
        (default: last chapter detected)

    Returns:
    ----------
    (list[ChapterInfo]): list of all chapter details extracted.
    """
    first_chapter = get_first_chapter_episode_no(session, series_url)
    episode_url = f"{viewer_url}&episode_no={first_chapter}"
    log.info("Sending request to '%s'", episode_url)
    resp = session.get(episode_url)
    soup = BeautifulSoup(resp.text, "lxml")
    _episode_cont = soup.find("div", class_="episode_cont").find_all("li")
    if not _episode_cont:
        return []

    chapter_details = [
        ChapterInfo(
            episode_details.find("span", {"class": "subj"}).text,
            chapter_number,
            int(episode_details["data-episode-no"]),
            episode_details.find("a")["href"],
        )
        for chapter_number, episode_details in enumerate(_episode_cont, start=1)
    ]

    return chapter_details[int(start_chapter or 1) - 1 : end_chapter]


def get_chapter_html(session: requests.Session, viewer_url: str, data_episode_num: int) -> str:
    """
    Download the HTML source of a chapter.

    Arguments:
    ----------
    session: requests.session
        the requests session object for persistent parameters.

    viewer_url: str
        chapter reader url of the series.

    data_episode_num: int
        chapter number to scrap image urls from.

    Returns:
    ----------
        complete HTML source
    """
    return session.get(f"{viewer_url}&episode_no={data_episode_num}").text


def download_chapter(
    chapter_download_task_id: TaskID,
    done_event: Event,
    progress: Progress,
    session: requests.Session,
    viewer_url: str,
    chapter_info: ChapterInfo,
    dest: str,
    zeros: int,
    images_format: str = "jpg",
    exporter: TextExporter | None = None,
) -> None:
    """
    downloads page starting of a given chapter, inclusive.
    stores the downloaded images into the dest path.

    Arguments:
    ----------
    chapter_download_task_id: int
        task of calling chapter download task

    session: requests.session
        the requests session object for persistent parameters.

    viewer_url: str
        chapter reader url of the series.

    chapter_number: int
        chapter to download

    zeros: int
        Number of padding digits used for naming the saved image file.

    dest:
        destination folder path to store the downloaded image files.
        (default: current working directory)

    exporter: TextExporter
        object responsible for exporting any texts, optional
    """
    log.debug("[italic red]Accessing[/italic red] chapter %d", chapter_info.chapter_number)
    html = get_chapter_html(session, viewer_url, chapter_info.data_episode_no)
    extractor = WebtoonViewerPageExtractor(html)
    img_urls = extractor.get_img_urls()
    if not os.path.exists(dest):
        os.makedirs(dest)
    if exporter:
        exporter.add_chapter_texts(
            chapter=chapter_info.chapter_number,
            title=extractor.get_chapter_title(),
            notes=extractor.get_chapter_notes(),
        )
    progress.update(chapter_download_task_id, total=len(img_urls), rendered_total=len(img_urls))
    progress.start_task(chapter_download_task_id)
    page_digits = int(math.log10(len(img_urls) - 1)) + 1 if len(img_urls) > 1 else 1
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=10, max_workers=4) as pool:
        for page_number, url in enumerate(img_urls):
            pool.submit(
                download_image,
                chapter_download_task_id,
                progress,
                url,
                dest,
                chapter_info.chapter_number,
                page_number,
                zeros,
                image_format=images_format,
                page_digits=page_digits,
            )
            if done_event.is_set():
                return

    log.info(
        "Chapter %d download complete with a total of %d pages [green]✓",
        chapter_info.chapter_number,
        len(img_urls),
    )
    progress.remove_task(chapter_download_task_id)


def setup_session() -> requests.Session:
    """
    Set up a requests session for downloading the webtoon.
    """
    session = requests.session()
    session.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")
    return session


def download_webtoon(
    progress: Progress,
    done_event: Event,
    series_url: str,
    start_chapter: int,
    end_chapter: int,
    dest: str,
    images_format: str = "jpg",
    download_latest_chapter: bool = False,
    separate_chapters: bool = False,
    exporter: TextExporter | None = None,
) -> None:
    """
    downloads all chapters starting from start_chapter until end_chapter, inclusive.
    stores the downloaded chapter into the dest path.

    Arguments:
    ----------
    series_url: str
        url of the series to scrap from the webtoons.com website,
        the url provided should be in the following format:
        https://www.webtoons.com/en/{?}/{?}/list?title_no={?}

    start_chapter: int
        starting range of chapters to download.
        (default: first chapter detected)

    end_chapter: int
        end range of chapter to download, inclusive of this chapter number.
        (default: last chapter detected)

    dest: str
        destination folder path to store the downloaded image files of the chapter.
        (default: current working directory)

    separate_chapters: bool
        separate downloaded chapters in their own folder under the dest path if true,
        else stores all images in the dest folder.

    exporter: TextExporter
        object responsible for exporting any texts, optional
    """
    session = setup_session()
    resp = session.get(series_url, headers=headers)
    extractor = WebtoonMainPageExtractor(resp.text)

    viewer_url = extractor.get_chapter_viewer_url()
    series_title = extractor.get_series_title()

    if not (dest):
        dest = slugify_file_name(series_title)

    if not os.path.exists(dest):
        log.warning("Creading Directory: [#80BBA6]%s[/]", dest)
        os.makedirs(dest)  # creates directory and sub-dirs if dest path does not exist
    else:
        log.warning("Directory Exists: [#80BBA6]%s[/]", dest)

    if exporter:
        exporter.set_dest(dest)
        exporter.add_series_texts(summary=extractor.get_series_summary())

    progress.console.print(f"Downloading [italic medium_spring_green]{series_title}[/] from {series_url}")
    n_downloads = download_chapters(
        session,
        progress,
        done_event,
        series_url,
        start_chapter,
        end_chapter,
        viewer_url,
        dest,
        images_format,
        download_latest_chapter,
        separate_chapters,
        exporter,
    )
    rich.print(
        f'Successfully Downloaded [red]{n_downloads}[/] {"chapter" if n_downloads <= 1 else "chapters"} of [medium_spring_green]{series_title}[/] in [italic plum2]{os.path.abspath(dest)}[/].'
    )


def download_chapters(
    session,
    progress: Progress,
    done_event: Event,
    series_url: str,
    start_chapter: int,
    end_chapter: int,
    viewer_url: str,
    dest: str,
    images_format: str = "jpg",
    download_latest_chapter: bool = False,
    separate_chapters: bool = False,
    exporter: TextExporter | None = None,
) -> int:
    n_downloaded_chapters = 0

    with progress:
        if download_latest_chapter:
            chapters_to_download = [get_chapters_details(session, viewer_url, series_url)[-1]]

        else:
            chapters_to_download = get_chapters_details(session, viewer_url, series_url, start_chapter, end_chapter)

        start_chapter, end_chapter = (
            chapters_to_download[0].chapter_number,
            chapters_to_download[-1].chapter_number,
        )
        n_chapters_to_download = end_chapter - start_chapter + 1

        if download_latest_chapter:
            progress.console.log(f"[plum2]Latest Chapter[/] -> [green]{end_chapter}[/]")
        else:
            progress.console.log(
                f"[italic]start:[/] [green]{start_chapter}[/]  [italic]end:[/] [green]{end_chapter}[/] -> [italic]N of chapters:[/] [green]{n_chapters_to_download}[/]"
            )
        series_download_task = progress.add_task(
            "[green]Downloading Chapters...",
            total=n_chapters_to_download,
            type="Chapters",
            type_color="grey93",
            number_format=">02d",
            rendered_total=n_chapters_to_download,
        )

        # convert into an interable that can be consumed
        zeros = int(math.log10(end_chapter)) + 1

        if exporter:
            exporter.set_chapter_config(zeros, separate_chapters)

        def prepare_chapter_download(chapter_info: ChapterInfo) -> Future:
            chapter_dest = os.path.join(dest, get_chapter_dir(chapter_info, zeros, separate_chapters))
            chapter_download_task = progress.add_task(
                f"[plum2]Chapter {chapter_info.chapter_number}.",
                type="Pages",
                type_color="grey85",
                number_format=">02d",
                start=False,
                rendered_total="??",
            )
            return pool.submit(
                download_chapter,
                chapter_download_task,
                done_event,
                progress,
                session,
                viewer_url,
                chapter_info,
                chapter_dest,
                zeros,
                images_format,
                exporter,
            )

        print(f"number of chapters to download: {len(chapters_to_download)}")
        chapters_to_download = iter(chapters_to_download)
        with ThreadPoolExecutor(max_workers=4) as pool:
            chapter_download_futures = {
                prepare_chapter_download(chapter_info)
                for chapter_info in itertools.islice(chapters_to_download, N_CONCURRENT_CHAPTERS_DOWNLOAD)
            }
            while chapter_download_futures:
                done, chapter_download_futures = wait(chapter_download_futures, return_when=FIRST_COMPLETED)
                for fut in done:
                    if fut.exception():
                        log.error(
                            "Error occurred whilst trying to download chapter: %s",
                            fut.exception(),
                        )
                    else:
                        n_downloaded_chapters += 1
                        progress.update(series_download_task, advance=1)

                    if done_event.is_set():
                        return n_downloaded_chapters

                    chapter_download_futures.update(
                        prepare_chapter_download(chapter_info)
                        for chapter_info in itertools.islice(chapters_to_download, len(done))
                    )
    return n_downloaded_chapters
