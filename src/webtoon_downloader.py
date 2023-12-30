import binascii
import concurrent
import itertools
import json
import logging
import math
import m3u8
import os
import pathlib
import queue
import re
import shutil
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from threading import Event
from typing import List, Union
from urllib.parse import parse_qs, urlparse

import requests
import rich
from bs4 import BeautifulSoup
from PIL import Image
from rich import traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.text import Text

try:
    from .options import Options  # if installed as a module
except ImportError:
    from options import Options  # if running from source


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
    thumbnail_url: str
    """Thumbnail URL"""

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "sort_index", self.chapter_number)


@dataclass(order=True, frozen=True)
class MusicInfo:
    start: int
    """Image to start playback on"""
    end: int
    """Image to end playback on"""
    audioId: str
    """ID of audio-stream"""

    sort_index: int = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "sort_index", self.start)


class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, *args, maxsize=50, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)


class CustomTransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task) -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed", justify="center")
        return Text(
            f"{task.speed:2.0f} {task.fields.get('type')}/s",
            style="progress.data.speed",
            justify="center",
        )


class TextExporter:
    """Writes text elements to files, either to multiple plain text files
    or to a single JSON file, depending on selected export format."""

    def __init__(self, export_format: str):
        self.data = { 'chapters': {} }
        self.write_json = export_format in ["json", "all"]
        self.write_text = export_format in ["text", "all"]
        self.data_is_unchanged = False

    def set_chapter_config(self, zeros: int, separate: bool):
        self.separate = separate
        self.zeros = zeros

    def set_dest(self, dest: str):
        self.dest = dest

    def load_old_info(self):
        name = os.path.join(self.dest, "info.json")
        if not os.path.exists(name):
            return
        with open(name, "r") as f:
            self.data = json.load(f)
        if 'chapters' not in self.data:
            self.data['chapters'] = {}
        for c in list(self.data['chapters'].keys()):
            if type(c) == int:
                continue
            if type(c) != str or not c.isdigit():
                log.warning('Loaded unexpected chapters key "{c}"')
                continue
            chapter = self.data['chapters'].pop(c)
            self.data['chapters'][int(c)] = chapter
        self.data_is_unchanged = True

    def add_series_texts(self, summary: str):
        self.data_is_unchanged &= ('summary' in self.data
                and self.data['summary'] == summary)
        self.data['summary'] = summary
        if self.write_text:
            TextExporter._write_text(os.path.join(self.dest, "summary.txt"), summary)

    def has_chapter_texts(self, chapter: int):
        result = True
        if self.write_json:
            name = os.path.join(self.dest, "info.json")
            result &= os.path.exists(name)
            result &= chapter in self.data['chapters']
        if self.write_text:
            prefix = self._chapter_prefix(chapter)
            result &= os.path.exists(prefix + 'title.txt')
        return result

    def add_chapter_texts(self, chapter: int, title: str, notes: str):
        self.data_is_unchanged &= (chapter in self.data['chapters']
                and 'title' in self.data['chapters'][chapter]
                and self.data['chapters'][chapter]['title'] == title
                and ('notes' not in self.data['chapters'][chapter]) == (notes is None)
                and (notes is None or self.data['chapters'][chapter]['notes'] == notes))
        if chapter not in self.data['chapters']:
            self.data['chapters'][chapter] = { }
        self.data['chapters'][chapter]['title'] = title
        if notes is not None:
            self.data['chapters'][chapter]['notes'] = notes
        elif 'notes' in self.data['chapters'][chapter]:
            self.data['chapters'][chapter].pop('notes')
        if self.write_text:
            prefix = self._chapter_prefix(chapter)
            TextExporter._write_text(prefix + "title.txt", title)
            if notes is not None:
                TextExporter._write_text(prefix + "notes.txt", notes)

    def write_data(self):
        if self.write_json:
            name = os.path.join(self.dest, "info.json")
            if not self.data_is_unchanged:
                with open(name, "w") as f:
                    json.dump(self.data, f, sort_keys=True)

    def _chapter_prefix(self, chapter: int):
        prefix = self.dest
        if self.separate:
            prefix = os.path.join(prefix, f"{chapter:0{self.zeros}d}")
        return os.path.join(prefix, f"{chapter:0{self.zeros}d}_")

    def _write_text(name: str, text: str):
        if not os.path.exists(name):
            with open(name, "w") as f:
                f.write(text + '\n')


######################## Header Configuration ################################
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
image_headers = {"referer": "https://www.webtoons.com/", **headers}
###########################################################################

progress = Progress(
    TextColumn("{task.description}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.2f}%",
    "•",
    SpinnerColumn(style="progress.data.speed"),
    CustomTransferSpeedColumn(),
    "•",
    TextColumn(
        "[green]{task.completed:>02d}[/]/[bold green]{task.fields[rendered_total]}[/]",
        justify="left",
    ),
    SpinnerColumn(),
    "•",
    TimeRemainingColumn(),
    transient=True,
    refresh_per_second=20,
)
######################## Log Configuration ################################
sys.stdout.reconfigure(encoding="utf-8")
console = Console()
traceback.install(console=console, show_locals=False)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
# create logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)  # set log level

# create formatter
CLI_FORMAT = "%(message)s"
FILE_FORMAT = "%(asctime)s - %(levelname)-8s - %(message)s - %(filename)s - %(lineno)d - %(name)s"  # rearranged

# create file handler
LOG_FILENAME = "webtoon_downloader.log"
file_handler = RotatingFileHandler(
    LOG_FILENAME, maxBytes=1000000, backupCount=10, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

console_handler = RichHandler(
    level=logging.WARNING,
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=False,
    markup=True,
)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter(CLI_FORMAT))
log.addHandler(file_handler)
log.addHandler(console_handler)
##################################################################

done_event = Event()
N_CONCURRENT_CHAPTERS_DOWNLOAD = 4


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


def get_background_url(style: str):
    """
    Extracts the URL of the background image from a CSS style declaration.

    Arguments:
    ----------
    style : the CSS style to parse

    Returns:
    --------
        The found URL or None if not found.
    """
    m = re.match('background:[^;]*url\((?P<URL>[^\)]*)\)', style)
    if m is None:
        return None
    return m.group('URL')


def get_series_background(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the URL of the series background image from the html of the series
    overview page.

    Arguments:
    ----------

    html : the html body of the scraped series overview page, passed either as a raw
           string or a bs4.BeautifulSoup object

    Returns:
    --------
        The URL of the background image or None if not found.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    node =  _html.find('div', class_='detail_bg')
    if node is None or 'style' not in node.attrs:
        return None
    return get_background_url(node.attrs['style'])


def get_series_banner(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the URL of the series banner image from the html of the series
    overview page.

    Arguments:
    ----------

    html : the html body of the scraped series overview page, passed either as a raw
           string or a bs4.BeautifulSoup object

    Returns:
    --------
        The URL of the banner image or None if not found.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    node =  _html.find('span', class_='thmb')
    if node is None:
        return None
    node =  node.find('img')
    if node is None:
        return None
    return node.attrs['src']


def get_series_thumbnail(html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the URL of the series thumbnail image from the html of the series
    overview page.

    Arguments:
    ----------

    html : the html body of the scraped series overview page, passed either as a raw
           string or a bs4.BeautifulSoup object

    Returns:
    --------
        The URL of the thumbnail image or None if not found.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    node =  _html.find('div', class_='detail_body')
    if node is None or 'style' not in node.attrs:
        return None
    return get_background_url(node.attrs['style'])


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


def get_chapter_music(html: Union[str, BeautifulSoup], img_urls: List[str]
    ) -> List[MusicInfo]:
    """
    Extracts the music to play in a chapter from the html of the chapter.

    Arguments:
    ----------

    html : the html body of the scraped chapter, passed either as a raw string or
           a bs4.BeautifulSoup object

    img_urls : list of image URLs, needed to detect start and end of music playback

    Returns:
    --------
        List of music to play, empty if none found.
    """
    _html = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html)
    script_tags = _html.find_all('script')
    script_texts = map(lambda tag: tag.text, script_tags)
    audio_scripts = filter(lambda txt: 'window.__audioProperties__' in txt,
                           script_texts)
    rx = re.compile('^\s*episodeBgmList\s*:\s*(?P<json>.*),\s*$', re.MULTILINE)
    rx_matches = map(lambda txt: rx.search(txt), audio_scripts)
    data_texts = map(lambda m: m.group('json'), rx_matches)
    data_list = map(lambda txt: json.loads(txt), data_texts)
    data = list(itertools.chain(*data_list))
    def convert(data):
        audioId = data['audioId']
        start_url = data['playImageUrl']
        end_url = data['stopImageUrl']
        def idx(url, dflt):
            if len(url) == 0:
                return dflt
            return next((i for i, e in enumerate(img_urls) if url in e), dflt)
        return MusicInfo(idx(start_url, 0), idx(end_url, len(img_urls)-1), audioId)
    return list(map(convert, data))


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
        return (
            BeautifulSoup(html)
            .find("li", attrs={"data-episode-no": True})
            .find("a")["href"]
            .split("&")[0]
        )

    if isinstance(html, BeautifulSoup):
        return (
            html.find("li", attrs={"data-episode-no": True})
            .find("a")["href"]
            .split("&")[0]
        )

    raise TypeError("variable passed is neither a string nor a BeautifulSoup object")


def get_first_chapter_episode_no(session: requests.session, series_url: str) -> int:
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
        href = soup.find("a", id="_btnEpisode")["href"]
        return int(parse_qs(urlparse(href).query)["episode_no"][0])
    except (TypeError, KeyError):
        # If the second attempt fails, try to get the first episode from the list
        soup = BeautifulSoup(session.get(f"{series_url}&page=9999").text, "html.parser")
        return min(
            int(episode["data-episode-no"])
            for episode in soup.find_all("li", {"class": "_episodeItem"})
        )


def get_chapters_details(
    session: requests.session,
    viewer_url: str,
    series_url: str,
    start_chapter: int = 1,
    end_chapter: int = None,
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
    chapter_details = [
        ChapterInfo(
            episode_details.find("span", {"class": "subj"}).text,
            chapter_number,
            int(episode_details["data-episode-no"]),
            episode_details.find("a")["href"],
            episode_details.find("span", class_="thmb").find("img")["data-url"]
        )
        for chapter_number, episode_details in enumerate(
            soup.find("div", class_="episode_cont").find_all("li"), start=1
        )
    ]

    return chapter_details[int(start_chapter or 1) - 1 : end_chapter]


def get_chapter_html(
    session: requests.session, viewer_url: str, data_episode_num: int
) -> str:
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
    return [
        url["data-url"]
        for url in _html.find("div", class_="viewer_img _img_viewer_area").find_all(
            "img"
        )
    ]


def get_img_urls(
    session: requests.session, viewer_url: str, data_episode_num: int
) -> list:
    """
    Extracts the url of all images of a given chapter of the series.

    Arguments:
    ----------
    session: requests.session
        the requests session object for persistent parameters.

    viewer_url: str
        chapter reader url of the series.

    data_episode_num: int
        chapter number to scrap image urls from, referenced as episode_no and data_episode_num.

    Returns:
    ----------
    (list[str]): list of all image urls extracted from the chapter.
    """
    return extract_img_urls(get_chapter_html(session, viewer_url, data_episode_num))


def image_exists(dest: str, image_base: str, image_format: str):
    path = pathlib.Path(dest)
    if image_format != 'native':
        file = path / f"{image_base}.{image_format}"
        return file.exists()
    else:
        files = list(path.glob(f"{image_base}.*"))
        return len(files) > 0


def image_prefix_exists(dest: str, image_prefix: str, image_format: str):
    path = pathlib.Path(dest)
    if image_format == 'native':
        pattern = f"{image_prefix}_0*.*"
    else:
        pattern = f"{image_prefix}_0*.{image_format}"
    files = list(path.glob(pattern))
    return len(files) > 0


def download_generic_image(
    task_id: int,
    url: str,
    dest: str,
    image_base: str,
    image_format: str = "native",
):
    """
    downloads a generic image (comic, thumbnail, ...) from a URL and converts it
    if desired.

    Arguments:
    ----------
    task_id: int
        task to report progress in.

    url: str
        image direct link.

    dest: str
        folder path where to save the downloaded image.

    image_base: str
        base filename without the dot and file-extension.

    image_format: str
        format of downloaded image: either native = whatever got downloaded or
        jpg/png = convert the image to one of these.
        (default: native)
    """
    if image_exists(dest, image_base, image_format):
        log.debug("Image %s already exists", image_base)
        progress.update(task_id, advance=1)
        return
    if url is None:
        log.debug("No URL for image %s provided", image_base)
        progress.update(task_id, advance=1)
        return
    log.debug("Requesting image %s", image_base)
    resp = requests.get(url, headers=image_headers, stream=True, timeout=5)
    progress.update(task_id, advance=1)
    if resp.status_code == 200:
        resp.raw.decode_content = True
        content_type = resp.headers.get('Content-Type')
        if content_type is None:
            log.warning('No Content-Type specified for {image_base}, defaulting to jpg')
            detected_format = 'jpg'
        elif 'image/jpeg' in content_type:
            detected_format = 'jpg'
        elif 'image/png' in content_type:
            detected_format = 'png'
        else:
            log.warning('Unknown Content-Type "{content_type}" for {image_base}, '
                        'defaulting to jpg')
            detected_format = 'jpg'
        if image_format == 'native' or image_format == detected_format:
            with open(os.path.join(dest, f"{image_base}.{detected_format}"), "wb") as f:
                shutil.copyfileobj(resp.raw, f)
        else:
            img = Image.open(resp.raw)
            if image_format == 'jpg' and img.mode != 'RGB':
                if 'transparency' in img.info:
                    img = img.convert('RGBA')
                img = img.convert('RGB')
            img.save(os.path.join(dest, f"{image_base}.{image_format}"))
    else:
        log.error(
            "[bold red blink]Unable to download image[/][medium_spring_green]%s[/], "
            "request returned error [bold red blink]%d[/]",
            image_base,
            resp.status_code,
        )


def download_image(
    chapter_download_task_id: int,
    url: str,
    dest: str,
    chapter_number: int,
    page_number: int,
    zeros: int,
    image_format: str = "native",
    page_digits: int = 1,
):
    """
    downloads an image using a direct url into the base path folder.

    Arguments:
    ----------
    chapter_download_task_id: int
        task of calling chapter download task

    url: str
        image direct link.

    dest: str
        folder path where to save the downloaded image.

    chapter_number: int
        chapter number used for naming the saved image file.

    page_number: str | int
        page number used for naming the saved image file.

    zeros: int
        Number of digits used for the chapter number

    image_format: str
        format of downloaded image: either native = whatever got downloaded or
        jpg/png = convert the image to one of these.
        (default: native)

    page_digits: int
        Number of digits used for the page number inside the chapter
    """
    image_base = f"{chapter_number:0{zeros}d}_{page_number:0{page_digits}d}"
    download_generic_image(chapter_download_task_id, url, dest, image_base, image_format)


def download_music_stream(
    task_id: int,
    info: MusicInfo,
    dest: str,
    chapter_number: int,
    chapter_digits: int,
    page_digits: int,
):
    """
    downloads one piece of background music from a streaming service.

    Arguments:
    ----------
    task_id: int
        task to report progress in.

    info: MusicInfo
        Scrapped info about the music piece to download

    dest: str
        folder path where to save the downloaded file.

    chapter_number: int
        chapter number used for naming the saved file.

    chapter_digits: int
        Number of digits used for the chapter number

    page_digits: int
        Number of digits used for the page number.
    """
    filename = (f"{chapter_number:0{chapter_digits}d}"
                f"_{info.start:0{page_digits}d}_{info.end:0{page_digits}d}.ts")
    filepath = os.path.join(dest, filename)
    if os.path.exists(filepath):
        log.debug("File %s already exists", filename)
        progress.update(task_id, advance=1)
        return
    log.debug("Requesting audio manifest for %s", filename)
    url = f'https://apis.naver.com/audiopweb/audiopplayapiweb/play/web/audio/{info.audioId}'
    resp = requests.get(url, image_headers, stream=True, timeout=5)
    if resp.status_code != 200:
        log.error(
            "[bold red blink]Unable to download audio manifest for[/][medium_spring_green]%s[/], "
            "request returned error [bold red blink]%d[/]",
            filename,
            resp.status_code,
        )
        progress.update(task_id, advance=1)
        return
    data = json.loads(resp.content)
    url = data['result']['hlsManifest']['url']
    playlist = m3u8.load(url)
    data = b''
    key = None
    for i, segment in enumerate(playlist.segments):
        decrypt = lambda x: x
        if segment.key.method == 'AES-128':
            if key is None:
                resp = requests.get(segment.key.uri, stream=True, timeout=5)
                if resp.status_code != 200:
                    log.error(
                        "[bold red blink]Unable to download decryption key "
                        "for[/][medium_spring_green]%s[/], "
                        "request returned error [bold red blink]%d[/]",
                        filename,
                        resp.status_code,
                    )
                    progress.update(task_id, advance=1)
                    return
                key = resp.content
            idx = playlist.media_sequence + i
            iv = binascii.a2b_hex(f'{idx:032x}')
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            decrypt = cipher.decrypt
        resp = requests.get(segment.uri, stream=True, timeout=5)
        if resp.status_code != 200:
            log.error(
                "[bold red blink]Unable to download audio chunk %d "
                "for[/][medium_spring_green]%s[/], "
                "request returned error [bold red blink]%d[/]",
                i,
                filename,
                resp.status_code,
            )
            progress.update(task_id, advance=1)
            return
        data += decrypt(resp.content)
    with open(filepath, 'wb') as f:
        f.write(data)
    progress.update(task_id, advance=1)


def exit_handler(sig, frame):
    """
    stops execution of the program.
    """
    done_event.set()
    progress.console.print("[bold red]Stopping Download[/]...")
    progress.console.print("[red]Download Stopped[/]!")
    progress.console.print("")
    sys.exit(0)


def download_chapter(
    chapter_download_task_id: int,
    session: requests.Session,
    viewer_url: str,
    chapter_info: ChapterInfo,
    dest: str,
    zeros: int,
    images_format: str = "jpg",
    exporter: TextExporter = None,
    extra_media: bool = False,
):
    """
    downloads pages starting of a given chapter, inclusive.
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

    extra_media: bool
        export extra media like thumbnails or music
    """
    prefix = f"{chapter_info.chapter_number:0{zeros}d}"
    already_downloaded = (
        os.path.exists(dest)
        and image_prefix_exists(dest, prefix, images_format)
        and (exporter is None or exporter.has_chapter_texts(chapter_info.chapter_number))
        and (not extra_media or image_exists(dest, f"{prefix}_thumbnail", images_format))
    )
    if already_downloaded:
        log.info("Chapter %d already present [green]✓", chapter_info.chapter_number)
        progress.remove_task(chapter_download_task_id)
        return
    log.debug(
        "[italic red]Accessing[/italic red] chapter %d", chapter_info.chapter_number
    )
    html = get_chapter_html(session, viewer_url, chapter_info.data_episode_no)
    soup = BeautifulSoup(html, "lxml")
    img_urls = extract_img_urls(soup)
    if not os.path.exists(dest):
        os.makedirs(dest)
    if exporter:
        exporter.add_chapter_texts(
                chapter=chapter_info.chapter_number,
                title=get_chapter_title(soup),
                notes=get_chapter_notes(soup))
    music = get_chapter_music(soup, img_urls)
    if extra_media:
        num_downloads = len(img_urls) + 1 + len(music)
    else:
        num_downloads = len(img_urls)
    progress.update(
        chapter_download_task_id, total=num_downloads, rendered_total=num_downloads
    )
    progress.start_task(chapter_download_task_id)
    page_digits = int(math.log10(len(img_urls) - 1)) + 1 if len(img_urls) > 1 else 1
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=10, max_workers=4) as pool:
        if extra_media:
            pool.submit(
                download_generic_image,
                chapter_download_task_id,
                chapter_info.thumbnail_url,
                dest,
                f"{prefix}_thumbnail",
                images_format,
            )
            for m in music:
                pool.submit(
                    download_music_stream,
                    chapter_download_task_id,
                    m,
                    dest,
                    chapter_info.chapter_number,
                    zeros,
                    page_digits,
                )
        for page_number, url in enumerate(img_urls):
            pool.submit(
                download_image,
                chapter_download_task_id,
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


def slugify_file_name(file_name: str) -> str:
    """
    Slugifies a file name by removing special characters, replacing spaces with underscores.
    Args:
        file_name: The original file name.

    Returns:
        str: The slugified file name.

    """
    # Replace leading/trailing whitespace and replace spaces with underscores
    # And remove special characters
    return re.sub(r"[^\w.-]", "", file_name.strip().replace(" ", "_"))


def get_chapter_dir(
    chapter_info: ChapterInfo,
    zeros: int,
    separate_chapters: bool
) -> str:
    """
    Get the relative directory to use for a chapter, given the supplied options.

    Arguments:
        chapter_info:      Information about this chapter
        zeros:             Number of digits to use for the chapter-number
        separate_chapters: Selector if each chapter should be its own directory

    Returns:
        Relative directory for files in chapter
    """
    if not separate_chapters:
        return '.'
    return f"{chapter_info.chapter_number:0{zeros}d}"


def download_webtoon(
    series_url: str,
    start_chapter: int,
    end_chapter: int,
    dest: str,
    images_format: str = "jpg",
    download_latest_chapter: bool = False,
    separate_chapters: bool = False,
    exporter: TextExporter = None,
    extra_media: bool = False,
):
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

    extra_media: bool
        export extra media like overview images, thumbnails or music
    """
    session = requests.session()
    session.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")
    resp = session.get(series_url, headers=headers)
    soup = BeautifulSoup(resp.text, "lxml")
    viewer_url = get_chapter_viewer_url(soup)
    series_title = get_series_title(soup)
    if not (dest):
        dest = slugify_file_name(series_title)
    if not os.path.exists(dest):
        log.warning("Creading Directory: [#80BBA6]%s[/]", dest)
        os.makedirs(dest)  # creates directory and sub-dirs if dest path does not exist
    else:
        log.warning("Directory Exists: [#80BBA6]%s[/]", dest)
    if exporter:
        exporter.set_dest(dest)
        exporter.load_old_info()
        exporter.add_series_texts(summary=get_series_summary(soup))

    progress.console.print(
        f"Downloading [italic medium_spring_green]{series_title}[/] from {series_url}"
    )
    with progress:
        if download_latest_chapter:
            chapters_to_download = [
                get_chapters_details(session, viewer_url, series_url)[-1]
            ]

        else:
            chapters_to_download = get_chapters_details(
                session, viewer_url, series_url, start_chapter, end_chapter
            )

        start_chapter, end_chapter = (
            chapters_to_download[0].chapter_number,
            chapters_to_download[-1].chapter_number,
        )
        n_chapters_to_download = end_chapter - start_chapter + 1

        if extra_media:
            extras_download_task = progress.add_task(
                "[green]Downloading extra images...",
                total=3,
                type="Images",
                type_color="grey85",
                number_format=">02d",
                rendered_total=3,
            )
            download_generic_image(extras_download_task, get_series_background(soup),
                    dest, 'background', images_format)
            download_generic_image(extras_download_task, get_series_banner(soup),
                    dest, 'banner', images_format)
            download_generic_image(extras_download_task, get_series_thumbnail(soup),
                    dest, 'thumbnail', images_format)
            progress.remove_task(extras_download_task)

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

        chapters_to_download = iter(
            chapters_to_download
        )  # convert into an interable that can be consumed
        zeros = int(math.log10(end_chapter)) + 1
        if exporter:
            exporter.set_chapter_config(zeros, separate_chapters)
        with ThreadPoolExecutor(max_workers=4) as pool:
            chapter_download_futures = set()
            for chapter_info in itertools.islice(
                chapters_to_download, N_CONCURRENT_CHAPTERS_DOWNLOAD
            ):
                chapter_dest = os.path.join(dest, get_chapter_dir(
                    chapter_info, zeros, separate_chapters))
                chapter_download_task = progress.add_task(
                    f"[plum2]Chapter {chapter_info.chapter_number}.",
                    type="Pages",
                    type_color="grey85",
                    number_format=">02d",
                    start=False,
                    rendered_total="??",
                )
                chapter_download_futures.add(
                    pool.submit(
                        download_chapter,
                        chapter_download_task,
                        session,
                        viewer_url,
                        chapter_info,
                        chapter_dest,
                        zeros,
                        images_format,
                        exporter,
                        extra_media,
                    )
                )

            while chapter_download_futures:
                # Wait for the next future to complete.
                done, chapter_download_futures = concurrent.futures.wait(
                    chapter_download_futures,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                for _ in done:
                    progress.update(series_download_task, advance=1)
                    if done_event.is_set():
                        return

                # Scheduling the next set of futures.
                for chapter_info in itertools.islice(chapters_to_download, len(done)):
                    chapter_dest = os.path.join(dest, get_chapter_dir(
                        chapter_info, zeros, separate_chapters))
                    chapter_download_task = progress.add_task(
                        f"[plum2]Chapter {chapter_info.chapter_number}.",
                        type="Pages",
                        type_color="grey85",
                        number_format=">02d",
                        start=False,
                        rendered_total="??",
                    )
                    chapter_download_futures.add(
                        pool.submit(
                            download_chapter,
                            chapter_download_task,
                            session,
                            viewer_url,
                            chapter_info,
                            chapter_dest,
                            zeros,
                            images_format,
                            exporter,
                            extra_media,
                        )
                    )

    rich.print(
        f'Successfully Downloaded [red]{n_chapters_to_download}[/] {"chapter" if n_chapters_to_download <= 1 else "chapters"} of [medium_spring_green]{series_title}[/] in [italic plum2]{os.path.abspath(dest)}[/].'
    )


def main():
    signal.signal(signal.SIGINT, exit_handler)
    parser = Options()
    parser.initialize()
    try:
        args = parser.parse()
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        sys.exit(1)
    assert not args.readme, "expected parser.parse() to handle readme: it didn't"
    series_url = args.url
    separate = args.seperate or args.separate
    exporter = TextExporter(args.export_format) if args.export_texts else None
    try:
        download_webtoon(
            series_url,
            args.start,
            args.end,
            args.dest,
            args.images_format,
            args.latest,
            separate,
            exporter,
            args.export_extra_media,
        )
        if exporter:
            exporter.write_data()
    except Exception as exc:
        log.exception(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
