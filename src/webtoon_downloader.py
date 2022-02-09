import concurrent
import itertools
import logging
import requests
import rich
import os
import pathlib
import queue
import shutil
import signal
import sys
import time
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from options import Options
from PIL import Image
from threading import Event
from typing import List, Union
from concurrent.futures import as_completed, ThreadPoolExecutor
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    Progress, 
    TextColumn, 
    TimeRemainingColumn,
    ProgressColumn,
    SpinnerColumn
)
from rich.text import Text
from rich.style import Style

@dataclass(order=True, frozen=True)
class ChapterInfo:
    sort_index: int = field(init=False, repr=False)
    title: str
    chapter_number: int #released chapter number
    data_episode_no: int #chapter number referenced by webtoon server
    content_url: str
    def __post_init__(self):
        object.__setattr__(self, 'sort_index', self.chapter_number)



class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, maxsize=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)

class CustomTransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text(f"?", style="progress.data.speed", justify='center')
        return Text(f"{task.speed:2.0f} {task.fields.get('type')}/s", style="progress.data.speed", justify='center')

######################## Header Configuration ################################
if os.name == 'nt':
    user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                  'AppleWebKit/537.36 (KHTML, like Gecko)' 
                  'Chrome/92.0.4515.107 Safari/537.36')
else:
    user_agent = ('Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)' 
                  'Gecko/20100101 Firefox/75.0')
headers = {
    'dnt': '1',
    'user-agent': user_agent,
    'accept-language': 'en-US,en;q=0.9',
}
image_headers = {
    'referer': 'https://www.webtoons.com/',
    **headers
}
###########################################################################

progress = Progress(    
    TextColumn("{task.description}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.2f}%",
    "•",
    SpinnerColumn(style="progress.data.speed"),
    CustomTransferSpeedColumn(),
    "•",
    TextColumn("[green]{task.completed:>02d}[/]/[bold green]{task.fields[rendered_total]}[/]", justify="left"),
    SpinnerColumn(),
    "•",
    TimeRemainingColumn(),
    transient=True,
    refresh_per_second=20
)
######################## Log Configuration ################################
console = Console()
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
log = logging.getLogger(__name__)
FORMAT = "%(message)s"
LOG_FILENAME = 'webtoon_downloader.log'

logging.basicConfig(
    level="WARNING", format=FORMAT, datefmt="[%X]", 
    handlers=[RichHandler(
        console=progress.console, 
        rich_tracebacks=True, 
        tracebacks_show_locals= True, 
        markup=True
    )]
)
###########################################################################

done_event = Event()
n_concurrent_chapters_download = 4


def get_series_title(series_url, html: Union[str, BeautifulSoup]) -> str:
    """
    Extracts the full title series from the html of the scraped url.

    Arguments:
    ----------

    series_url: str
        url of the series to scrap from the webtoons.com website
        series title are grabbed differently for webtoons of the challenge category
    html : str | BeautifulSoup  
        the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object 

    Returns:
    ----------
    (str): The full title of the series.
    """
    if 'challenge' in series_url.lower().split('/'):
        title_html_element = 'h3'
    else:
        title_html_element = 'h1'
    
    if isinstance(html, str):
        series_title = BeautifulSoup(html).find(title_html_element, class_='subj').text
    elif isinstance(html, BeautifulSoup):
        series_title = html.find(title_html_element, class_='subj').text
    else:
        raise TypeError('variable passed is neither a string nor a BeautifulSoup object')
    return series_title.replace('\n', '').replace('\t', '')

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
        return BeautifulSoup(html).find('li', attrs={'data-episode-no': True}).find('a')['href'].split('&')[0]
    elif isinstance(html, BeautifulSoup):
        return html.find('li', attrs={'data-episode-no': True}).find('a')['href'].split('&')[0]
    else:
        raise TypeError('variable passed is neither a string nor a BeautifulSoup object')

def get_chapters_details(session: requests.session, viewer_url: str, start_chapter: int = 1, end_chapter: int = None) -> List[ChapterInfo]:
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
    r = session.get(f'{viewer_url}&episode_no=1')
    soup = BeautifulSoup(r.text, 'lxml')
    chapter_details = [
        ChapterInfo(
            episode_details.find('span', {'class': 'subj'}).text, 
            chapter_number, 
            int(episode_details['data-episode-no']), 
            episode_details.find('a')['href']
        )
        for chapter_number, episode_details
        in enumerate(soup.find('div', class_='episode_cont').find_all('li'), start=1)]

    return chapter_details[int(start_chapter or 1) - 1:end_chapter]

def get_img_urls(session: requests.session, viewer_url: str, data_episode_num: int) -> list:
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
    r = session.get(f'{viewer_url}&episode_no={data_episode_num}')
    soup = BeautifulSoup(r.text, 'lxml')
    return [url['data-url'] 
        for url 
        in soup.find('div', class_='viewer_img _img_viewer_area').find_all('img')]

def download_image(chapter_download_task_id: int, url: str, dest: str, chapter_number: Union[str, int], page_number: Union[str, int], image_format:str='jpg'):
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
    
    chapter_number: str | int
        chapter number used for naming the saved image file.

    page_number: str | int
        page number used for naming the saved image file.

    image_format: str
        format of downloaded image .
        (default: jpg)
    """
    log.debug(f"Requesting chapter {chapter_number}: page {page_number}")
    r = requests.get(url, headers=image_headers, stream=True)
    progress.update(chapter_download_task_id, advance=1)
    if r.status_code == 200:
        r.raw.decode_content = True
        file_name = f'{chapter_number}_{page_number}'
        if(image_format == 'png'):
            Image.open(r.raw).save(os.path.join(dest, f'{file_name}.png'))
        else:
            with open(os.path.join(dest, f'{file_name}.jpg'), 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    else:
        log.error(f'[bold red blink]Unable to download page[/] [medium_spring_green]{page_number}[/]' 
                  f'from chapter [medium_spring_green]{chapter_number}[/], request returned' 
                  f'error [bold red blink]{r.status_code}[/]')

def exit_handler(sig, frame):
    """
    stops execution of the program.
    """
    done_event.set()
    progress.console.print('[bold red]Stopping Download[/]...')
    progress.console.print('[red]Download Stopped[/]!')
    progress.console.print('')
    sys.exit(0)

def download_chapter(chapter_download_task_id: int, session: requests.Session, viewer_url: str, chapter_info: ChapterInfo, dest: str, images_format: str='jpg'):
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
    
    dest:
        destination folder path to store the downloaded image files.
        (default: current working directory)
    """
    log.debug(f'[italic red]Accessing[/italic red] chapter {chapter_info}')
    img_urls = get_img_urls(
            session = session,
            viewer_url = viewer_url,
            data_episode_num = chapter_info.data_episode_no
        )
    if not os.path.exists(dest):
        os.makedirs(dest)
    progress.update(chapter_download_task_id, total=len(img_urls), rendered_total=len(img_urls))
    progress.start_task(chapter_download_task_id)
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=10, max_workers=4) as pool:
        for page_number, url in enumerate(img_urls):
            pool.submit(download_image, chapter_download_task_id, url, dest, chapter_info.chapter_number, page_number, image_format=images_format)
            if done_event.is_set():
                return
    log.info(f'Chapter {chapter_info.chapter_number} download complete with a total of {len(img_urls)} pages [green]✓')
    progress.remove_task(chapter_download_task_id)
    
def download_webtoon(series_url: str, start_chapter: int, end_chapter: int, dest: str, images_format: str='jpg', download_latest_chapter=False, seperate_chapters=False):
    """
    downloads all chaptersstarting from start_chapter until end_chapter, inclusive.
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

    seperate_chapters: bool
        seperate downloaded chapters in their own folder under the dest path if true, 
        else stores all images in the dest folder.
    """
    session = requests.session()
    session.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")
    r = session.get(f'{series_url}', headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    viewer_url = get_chapter_viewer_url(soup)
    series_title = get_series_title(series_url, soup)
    if not(dest):
        dest = series_title.replace(" ", "_") #uses title name of series as folder name if dest is None
    if not os.path.exists(dest):
        log.warning(f'Creading Directory: [#80BBA6]{dest}[/]')
        os.makedirs(dest) #creates directory and sub-dirs if dest path does not exist
    else:
        log.warning(f'Directory Exists: [#80BBA6]{dest}[/]')

    progress.console.print(f'Downloading [italic medium_spring_green]{series_title}[/] from {series_url}')
    with progress:
        if download_latest_chapter:
            chapters_to_download = [get_chapters_details(session, viewer_url)[-1]]

        else:
            chapters_to_download = get_chapters_details(session, viewer_url, start_chapter, end_chapter)

        start_chapter, end_chapter = chapters_to_download[0].chapter_number, chapters_to_download[-1].chapter_number
        n_chapters_to_download = end_chapter - start_chapter + 1

        if download_latest_chapter:
            progress.console.log(f"[plum2]Latest Chapter[/] -> [green]{end_chapter}[/]")
        else:
            progress.console.log(f"[italic]start:[/] [green]{start_chapter}[/]  [italic]end:[/] [green]{end_chapter}[/] -> [italic]N of chapters:[/] [green]{n_chapters_to_download}[/]")
        series_download_task = progress.add_task(
            "[green]Downloading Chapters...", 
            total=n_chapters_to_download, type='Chapters', type_color='grey93', number_format='>02d', rendered_total=n_chapters_to_download)

        chapters_to_download = iter(chapters_to_download) # convert into an interable that can be consumed
        with ThreadPoolExecutor(max_workers=4) as pool:
            chapter_download_futures = set()
            for chapter_info in itertools.islice(chapters_to_download, n_concurrent_chapters_download):
                    chapter_dest = os.path.join(dest, str(chapter_info.chapter_number)) if seperate_chapters else dest
                    chapter_download_task = progress.add_task(f"[plum2]Chapter {chapter_info.chapter_number}.",  type='Pages', type_color='grey85', number_format='>02d', start=False, rendered_total='??')
                    chapter_download_futures.add(
                        pool.submit(download_chapter, chapter_download_task, session, viewer_url, chapter_info, chapter_dest, images_format)
                    )
                
            while chapter_download_futures:
                # Wait for the next future to complete.
                done, chapter_download_futures = concurrent.futures.wait(
                    chapter_download_futures, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for _ in done:
                    progress.update(series_download_task, advance=1)
                    if done_event.is_set():
                        return

                # Scheduling the next set of futures.
                for chapter_info in itertools.islice(chapters_to_download, len(done)):
                    chapter_dest = os.path.join(dest, str(chapter_info.chapter_number)) if seperate_chapters else dest
                    chapter_download_task = progress.add_task(f"[plum2]Chapter {chapter_info.chapter_number}.", type='Pages', type_color='grey85', number_format='>02d', start=False, rendered_total='??')
                    chapter_download_futures.add(
                        pool.submit(download_chapter, chapter_download_task, session, viewer_url, chapter_info, chapter_dest, images_format)
                    )
    
    rich.print(f'Successfully Downloaded [red]{n_chapters_to_download}[/] {"chapter" if n_chapters_to_download <= 1 else "chapters"} of [medium_spring_green]{series_title}[/] in [italic plum2]{os.path.abspath(dest)}[/].')

def main():
    signal.signal(signal.SIGINT, exit_handler)
    parser = Options()
    parser.initialize()
    try:
        args = parser.parse()
    except Exception as e:
        console.print(f'[red]Error:[/] {e}')
        return -1
    if args.readme:
        parent_path = pathlib.Path(__file__).parent.parent.resolve()     
        with open(os.path.join(parent_path, "README.md")) as readme:
            markdown = Markdown(readme.read())
            console.print(markdown)
            return
    series_url = args.url
    download_webtoon(series_url, args.start, args.end, args.dest, args.images_format, args.latest, args.seperate)

if(__name__ == '__main__'):
    main()