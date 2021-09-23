import logging
import requests
import rich
import os
import pathlib
import shutil
import signal
import sys
import time
from PIL import Image
from bs4 import BeautifulSoup
from threading import Event
from typing import Union
import concurrent
from concurrent.futures import as_completed, ThreadPoolExecutor
import queue
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    Progress, 
    TaskID,
    TextColumn, 
    TimeRemainingColumn,
    ProgressColumn
)
from rich.text import Text
from options import Options
from rich.style import Style
import itertools
pages_progress_style = Style(color="red", blink=True, bold=True)

class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, maxsize=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)

class ChapterDownloadProgress(Progress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def add_task(self, *args, **kwargs):
        super().add_task(*args, **kwargs)
        self.download_type = download_type


######################## Log Configuration ################################
console = Console()
log = logging.getLogger("rich")
FORMAT = "%(message)s"
LOG_FILENAME = 'webtoon_downloader.log'
logging.basicConfig(
    level="WARNING", format=FORMAT, datefmt="[%X]", 
    handlers=[RichHandler(console=console, rich_tracebacks=True, tracebacks_show_locals= True, markup=True)]
)
###########################################################################

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
    TextColumn("[#DAF7A6]{task.completed:>02d}/{task.total}[/#DAF7A6]", justify="left"),
    TextColumn("{task.fields[type]}", justify="left"),
    "*",
    TimeRemainingColumn(),
    transient=True
)
done_event = Event()


def get_series_title(html: Union[str, BeautifulSoup]) -> str:
    '''
    Extracts the full title series from the html of the scraped url.

    Arguments:
    ----------
    html : str | BeautifulSoup  
        the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object 

    Returns:
    ----------
    (str): The full title of the series.
    '''
    if isinstance(html, str):
        return BeautifulSoup(html).find('h1', class_='subj').text
    elif isinstance(html, BeautifulSoup):
        return html.find('h1', class_='subj').text
    else:
        raise TypeError('variable passed is neither a string nor a BeautifulSoup object')

def get_number_of_chapters(html: Union[str, BeautifulSoup]) -> int:
    '''
    Extracts the total number of chapters from the html of the scraped url.

    Arguments:
    ----------
    html : str | BeautifulSoup  
        the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object 

    Returns:
    ----------
    (int): The total number of chapters title of the series.
    '''
    if isinstance(html, str):
        return int(BeautifulSoup(html).find('li', attrs={"data-episode-no": True})['data-episode-no'])
    elif isinstance(html, BeautifulSoup):
        return int(html.find('li', attrs={"data-episode-no": True})['data-episode-no'])
    else:
        raise TypeError('variable passed is neither a string nor a BeautifulSoup object')

def get_chapter_viewer_url(html: Union[str, BeautifulSoup]) -> str:
    '''
    Extracts the url of the webtoon chapter reader related to the series given in the series url.

    Arguments:
    ----------
    html : str | BeautifulSoup  
        the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object 

    Returns:
    ----------
    (str): chapter reader url.
    '''
    if isinstance(html, str):
        return BeautifulSoup(html).find('li', attrs={'data-episode-no': True}).find('a')['href'].split('&')[0]
    elif isinstance(html, BeautifulSoup):
        return html.find('li', attrs={'data-episode-no': True}).find('a')['href'].split('&')[0]
    else:
        raise TypeError('variable passed is neither a string nor a BeautifulSoup object')

def get_img_urls(session: requests.session, viewer_url: str, chapter_number: int) -> list[str]:
    '''
    Extracts the url of all images of a given chapter of the series.

    Arguments:
    ----------
    session: requests.session
        the requests session object for persistent parameters.

    viewer_url: str
        chapter reader url of the series.
    
    chapter_number: int
        chapter number to scrap image urls from.

    Returns:
    ----------
    (list[str]): list of all image urls extracted from the chapter.
    '''
    r = session.get(f'{viewer_url}&episode_no={chapter_number}')
    soup = BeautifulSoup(r.text, 'lxml')
    return [url['data-url'] 
        for url 
        in soup.find('div', class_='viewer_img _img_viewer_area').find_all('img')]

def download_image(task_id, url: str, dest: str, chapter_number: Union[str, int], page_number: Union[str, int], image_format:str='jpg'):
    '''
    downloads an image using a direct url into the base path folder.

    Arguments:
    ----------
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
    '''
    #progress.console.log(f"Requesting chapter {chapter_number}: page {page_number}")
    r = requests.get(url, headers=image_headers, stream=True)
    progress.update(task_id, advance=1)
    if r.status_code == 200:
        #progress.console.log('STATUS 200')
        #progress.start_task(task_id)
        r.raw.decode_content = True
        file_name = f'{chapter_number}_{page_number}'
        if(image_format == 'png'):
            im = Image.open(r.raw).save(os.path.join(dest, f'{file_name}.png'))
        else:
            with open(os.path.join(dest, f'{file_name}.jpg'), 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        progress.console.log(f"Downloaded {path}")
    else:
        log.error(f'[bold red blink]Unable to download page[/] [medium_spring_green]{page_number}[/]' 
                  f'from chapter [medium_spring_green]{chapter_number}[/], request returned' 
                  f'error [bold red blink]{r.status_code}[/]')

def exit_handler(sig, frame):
    '''
    stops execution of the program.
    '''
    done_event.set()
    progress.console.print('[bold red]Stopping Download[/]...')
    time.sleep(2)
    progress.console.print('[red]Download Stopped[/]!')
    progress.console.print('')
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, exit_handler)
    parser = Options()
    parser.initialize()
    args = parser.parse()
    if args.readme:
        parent_path = pathlib.Path(__file__).parent.parent.resolve()     
        with open(os.path.join(parent_path, "README.md")) as readme:
            markdown = Markdown(readme.read())
            console.print(markdown)
            return
    series_url = args.url
    download_webtoon(series_url, args.start, args.end, args.dest, args.images_format)


def download_chapter(session: requests.Session, viewer_url: str, chapter_number: int, dest: str, images_format: str='jpg'):
    '''
    downloads pages starting of a given chapter, inclusive.
    stores the downloaded images into the dest path.

    Arguments:
    ----------
    session: requests.session
        the requests session object for persistent parameters.
    
    viewer_url: str
        chapter reader url of the series.
    
    chapter_number: int
        chapter to download
    
    dest:
        destination folder path to store the downloaded image files.
        (default: current working directory)
    '''
    progress.console.log(f'[italic red]Downloading[/italic red] chapter {chapter_number}:')
    progress.console.log
    img_urls = get_img_urls(
            session = session,
            viewer_url=viewer_url,
            chapter_number=chapter_number
        )
    chapter_download_task = progress.add_task(f"[plum2]Chapter {chapter_number}.", total=len(img_urls), type='Pages', number_format='>02d')
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=20, max_workers=4) as pool:
        for page_number, url in enumerate(img_urls):
            pool.submit(download_image, chapter_download_task, url, dest, chapter_number, page_number, image_format=images_format)
            if done_event.is_set():
                return
        progress.remove_task(chapter_download_task)
    rich.print(f'chapter {chapter_number} download complete with a total of {len(img_urls)} pages [green]✓')
    
def download_webtoon(series_url: str, start_chapter: int, end_chapter: int, dest: str, images_format: str='jpg'):
    '''
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
        (default: 1)
    
    end_chapter: int
        end range of chapter to download, inclusive of this chapter number.
        (default: last chapter detected)
    
    dest:
        destination folder path to store the downloaded image files of the chapter.
        (default: current working directory)

    '''
    session = requests.session()
    session.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
    session.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")
    r = session.get(f'{series_url}', headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    viewer_url = get_chapter_viewer_url(soup)
    series_title = get_series_title(soup)
    log.info(f'Series Title Acquired: [#80BBA6]{series_title}[/]')
    if not(dest):
        dest = series_title.replace(" ", "_") #uses title name of series as folder name if dest is None
    if not os.path.exists(dest):
        log.info(f'Creading Directory: [#80BBA6]{dest}[/]')
        os.makedirs(dest) #creates directory and sub-dirs if dest path does not exist

    console.print(f'Downloading [italic medium_spring_green]{series_title}[/] from {series_url}')
    with progress:
        if end_chapter == None:
            n_chapters = get_number_of_chapters(soup)
        else:
            n_chapters = end_chapter
        series_download_task = progress.add_task(
            "[green]Downloading Chapters...", 
            total=n_chapters - start_chapter + 1, type='Chapters', number_format='>02d')
        for chapter_number in range(start_chapter, n_chapters + 1):
            download_chapter(session, viewer_url, chapter_number, dest, images_format)
            progress.update(series_download_task, advance=1)

if(__name__ == '__main__'):
    main()