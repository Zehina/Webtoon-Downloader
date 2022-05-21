import concurrent
import itertools
from download_details import DownloadSettings
from dataclasses import dataclass, field
from typing import List, Union
from bs4 import BeautifulSoup
import requests
import os
import queue
from threads.thread_pool import ThreadPoolExecutorWithQueueSizeLimit
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import signal
import shutil
from PIL import Image
import sys

@dataclass(order=True)
class Series:
    series_url: str
    series_title: str = ""
    viewer_url: str = ""

@dataclass(order=True, frozen=True)
class ChapterInfo:
    sort_index: int = field(init=False, repr=False)
    title: str
    chapter_number: int #released chapter number
    data_episode_no: int #chapter number referenced by webtoon server
    content_url: str
    def __post_init__(self):
        object.__setattr__(self, 'sort_index', self.chapter_number)

class WebtoonSession():
    def __init__(self, series: Series, download_settings: DownloadSettings, log, progress, headers=None):
        self.download_settings = download_settings
        self.series = series
        if not headers:
            user_agent = self.setup_user_agent()
            self.setup_headers(user_agent)
        self.setup_session()
        self.log = log
        self.progress = progress
        self.done_event = Event()
        signal.signal(signal.SIGINT, self.exit_handler)

    def exit_handler(self, sig, frame):
        """
        stops execution of the program.
        """
        self.done_event.set()
        self.progress.console.print('[bold red]Stopping Download[/]...')
        self.progress.console.print('[red]Download Stopped[/]!')
        self.progress.console.print('')
        sys.exit(0)

    def download(self, compress_cbz=False):
        """
        downloads all chapters starting from start_chapter until end_chapter, inclusive.
        stores the downloaded chapter into the dest path.
        """
        r = self.session.get(f'{self.series.series_url}', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        self.series.viewer_url = self.extract_chapter_viewer_url(soup)
        self.series.series_title = self.extract_series_title(soup)
        
        dest = self.download_settings.dest or self.series.series_title.replace(" ", "_")
        if not os.path.exists(dest):
            self.progress.print(f'Creading Directory: [#80BBA6]{dest}[/]')
            self.log.info(f'Directory Exists: [#80BBA6]{dest}[/]')
            os.makedirs(dest) #creates directory and sub-dirs if dest path does not exist
        else:
            self.progress.print(f'Creading Directory: [#80BBA6]{dest}[/]')
            self.log.warning(f'Directory Exists: [#80BBA6]{dest}[/]')

        self.progress.console.print(f'Downloading [italic medium_spring_green]{self.series.series_title}[/] from {self.series.series_url}')
        with self.progress:
            chapters_to_download = self.get_chapters_details(start=self.download_settings.start, end=self.download_settings.end, latest=self.download_settings.latest)
            start_chapter, end_chapter = chapters_to_download[0].chapter_number, chapters_to_download[-1].chapter_number
            n_chapters_to_download = end_chapter - start_chapter + 1
            if self.download_settings.latest:
                self.progress.console.log(f"[plum2]Latest Chapter[/] -> [green]{end_chapter}[/]")
            else:
                self.progress.console.log(f"[italic]start:[/] [green]{start_chapter}[/]  [italic]end:[/] [green]{end_chapter}[/] -> [italic]N of chapters:[/] [green]{n_chapters_to_download}[/]")
            series_download_task = self.progress.add_task(
                "[green]Downloading Chapters...", 
                total=n_chapters_to_download, type='Chapters', type_color='grey93', number_format='>02d', rendered_total=n_chapters_to_download)

            chapters_to_download = iter(chapters_to_download) # convert into an interable that can be consumed
            with ThreadPoolExecutor(max_workers=4) as pool:
                chapter_download_futures = set()
                for chapter_info in itertools.islice(chapters_to_download, self.download_settings.max_concurrent):
                        chapter_dest = os.path.join(dest, str(chapter_info.chapter_number)) if self.download_settings.separate else dest
                        chapter_download_task = self.progress.add_task(f"[plum2]Chapter {chapter_info.chapter_number}.",  type='Pages', type_color='grey85', number_format='>02d', start=False, rendered_total='??')
                        chapter_download_futures.add(
                            pool.submit(self.download_chapter, chapter_download_task, chapter_info, chapter_dest)
                        )
                    
                while chapter_download_futures:
                    # Wait for the next future to complete.
                    done, chapter_download_futures = concurrent.futures.wait(
                        chapter_download_futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in done:
                        try:
                            result = future.result()
                        except Exception as exc:
                            self.log.critical(f"{future} failed with chapter info {exc}")
                            self.progress.print(f'download chapter task {future} generated an exception: {exc}')
                        self.progress.update(series_download_task, advance=1)
                        if self.done_event.is_set():
                            return

                    # Scheduling the next set of futures.
                    for chapter_info in itertools.islice(chapters_to_download, len(done)):
                        chapter_dest = os.path.join(dest, str(chapter_info.chapter_number)) if self.download_settings.separate else dest
                        chapter_download_task = self.progress.add_task(f"[plum2]Chapter {chapter_info.chapter_number}.", type='Pages', type_color='grey85', number_format='>02d', start=False, rendered_total='??')
                        chapter_download_futures.add(
                            pool.submit(self.download_chapter, chapter_download_task, chapter_info, chapter_dest)
                        )
        self.progress.print(f'Successfully Downloaded [red]{n_chapters_to_download}[/] {"chapter" if n_chapters_to_download <= 1 else "chapters"} of [medium_spring_green]{self.series.series_title}[/] in [italic plum2]{os.path.abspath(dest)}[/].')

    def setup_user_agent(self) -> str:
        import os
        if os.name == 'nt':
            user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                               'AppleWebKit/537.36 (KHTML, like Gecko)' 
                               'Chrome/92.0.4515.107 Safari/537.36')
        else:
            user_agent = ('Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)' 
                               'Gecko/20100101 Firefox/75.0')
        return user_agent

    def setup_headers(self, user_agent: str) -> None:
        self.headers = {
            'dnt': '1',
            'user-agent': user_agent,
            'accept-language': 'en-US,en;q=0.9',
        }
        self.image_headers = {
            'referer': 'https://www.webtoons.com/',
            **self.headers
        }

    def setup_session(self):
        self.session = requests.session()
        self.session.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
        self.session.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
        self.session.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")

    def extract_chapter_viewer_url(self, html: Union[str, BeautifulSoup]) -> str:
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

    def get_chapters_details(self, start: int=1, end: int=None, **kwargs) -> List[ChapterInfo]:
        """
        Extracts data about all chapters of the series.

        Returns:
        ----------
        (list[ChapterInfo]): list of all chapter details extracted.
        """
        r = self.session.get(f'{self.series.viewer_url}&episode_no=1')
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

        if kwargs.get('latest'):
            return [chapter_details[-1]]
        return chapter_details[(start or 1) - 1: (end or len(chapter_details))]
        
    def extract_series_title(self, html: Union[str, BeautifulSoup]) -> str:
        """
        Extracts the full title series from the html of the scraped url.

        Arguments:
        ----------
        html : str | BeautifulSoup  
            the html body of the scraped series url, passed either as a raw string or a bs4.BeautifulSoup object 

        Returns:
        ----------
        (str): The full title of the series.
        """
        if 'challenge' in self.series.series_url.lower().split('/'):
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

    def extract_img_urls(self, data_episode_num: int) -> list:
        """
        Returns:
        ----------
        (list[str]): list of all image urls extracted from the chapter.
        """
        r = self.session.get(f'{self.series.viewer_url}&episode_no={data_episode_num}')
        soup = BeautifulSoup(r.text, 'lxml')
        return [url['data-url'] 
            for url 
            in soup.find('div', class_='viewer_img _img_viewer_area').find_all('img')]

    def download_image(self, chapter_download_task_id: int, url: str, dest: str, chapter_number: Union[str, int], page_number: Union[str, int], image_format:str='jpg'):
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
        self.log.debug(f"Requesting chapter {chapter_number}: page {page_number}")
        r = requests.get(url, headers=self.image_headers, stream=True)
        self.progress.update(chapter_download_task_id, advance=1)
        if r.status_code == 200:
            r.raw.decode_content = True
            file_name = f'{chapter_number}_{page_number}'
            final_file_name = ''
            if(image_format == 'png'):
                final_file_name = os.path.join(dest, f'{file_name}.png')
                Image.open(r.raw).save(final_file_name)
            else:
                final_file_name = os.path.join(dest, f'{file_name}.jpg')
                with open(final_file_name, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

            return final_file_name
        else:
            log.error(f'[bold red blink]Unable to download page[/] [medium_spring_green]{page_number}[/]' 
                    f'from chapter [medium_spring_green]{chapter_number}[/], request returned' 
                    f'error [bold red blink]{r.status_code}[/]')

    def download_chapter(self, chapter_download_task_id: int, chapter_info: ChapterInfo, dest: str, images_format: str='jpg', compress_cbz=False):
        """
        downloads pages starting of a given chapter, inclusive.
        stores the downloaded images into the dest path.

        Arguments:
        ----------
        chapter_download_task_id: int
            task of calling chapter download task
        
        chapter_number: int
            chapter to download
        
        dest: str
            destination folder path to store the downloaded image files.
            (default: current working directory)
        """
        
        self.log.debug(f'[italic red]Accessing[/italic red] chapter {chapter_info}')
        img_urls = self.extract_img_urls(
                data_episode_num = chapter_info.data_episode_no
            )
        if not os.path.exists(dest):
            os.makedirs(dest)
        self.progress.update(chapter_download_task_id, total=len(img_urls), rendered_total=len(img_urls))
        self.progress.start_task(chapter_download_task_id)
        with ThreadPoolExecutorWithQueueSizeLimit(maxsize=10, max_workers=4) as pool:
            image_download_futures = set()
            for page_number, url in enumerate(img_urls):
                image_download_futures.add(
                    pool.submit(self.download_image, chapter_download_task_id, url, dest, chapter_info.chapter_number, page_number, image_format=images_format)
                )
                if self.done_event.is_set():
                    return

            concurrent.futures.wait(image_download_futures, return_when=concurrent.futures.ALL_COMPLETED)
            for future in image_download_futures:
                try:
                    future.result()
                except BaseException as e:
                    raise e
            # if compress_cbz:
            #     self.log.info('cbz enabled')
            #     with zipfile.ZipFile(f'{dest}.cbz', 'w') as cbz_zip:
            #         for future in image_download_futures:
            #             image_file_path = future.result()
            #             image_folder, image_file_name = os.path.split(image_file_path)
            #             cbz_zip.write(image_file_path, compress_type=zipfile.ZIP_STORED, arcname=image_file_name)

        self.log.info(f'Chapter {chapter_info.chapter_number} download complete with a total of {len(img_urls)} pages [green]✓')
        self.progress.remove_task(chapter_download_task_id)