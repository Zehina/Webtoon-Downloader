import concurrent
import itertools
import os
import signal
import sys
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import List, Union
from WebtoonDownloader.classes.tasks.chapter_download_task import download_chapter
from WebtoonDownloader.classes.DownloadSettings import DownloadSettings
from WebtoonDownloader.classes.WebtoonSession import WebtoonSession
from WebtoonDownloader.classes.Series import ChapterInfo, Series

class WebtoonDownloader():
    def __init__(self, series: Series, download_settings: DownloadSettings, log, progress):
        self.download_settings = download_settings
        self.series = series
        self.session = WebtoonSession()
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
        r = self.session.get(f'{self.series.series_url}')
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
            with ThreadPoolExecutor(max_workers=6) as pool:
                chapter_download_futures = set()
                for chapter_info in itertools.islice(chapters_to_download, self.download_settings.max_concurrent):
                        chapter_dest = os.path.join(dest, str(chapter_info.chapter_number)) if self.download_settings.separate else dest
                        chapter_download_task = self.progress.add_task(f"[plum2]Chapter {chapter_info.chapter_number}.",  type='Pages', type_color='grey85', number_format='>02d', start=False, rendered_total='??')
                        chapter_download_futures.add(
                            self.submit_chapter_download_task(
                                pool, 
                                chapter_download_task_id=chapter_download_task, 
                                dest=chapter_dest, 
                                chapter_info=chapter_info, 
                                image_extractor= lambda x=chapter_info.data_episode_no: self.extract_img_urls(x),
                                setup_progress= lambda total_imgs, x=chapter_download_task: self.setup_chapter_task_progress(x, total_imgs),
                                progress_notifier= lambda x=chapter_download_task: self.progress_chapter_download_task(x),
                                completion_notifier= lambda x=chapter_download_task: self.chapter_task_completion(x)
                            )
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
                            self.submit_chapter_download_task(
                                pool, 
                                chapter_download_task_id=chapter_download_task, 
                                dest=chapter_dest, 
                                chapter_info=chapter_info, 
                                image_extractor= lambda x=chapter_info.data_episode_no: self.extract_img_urls(x),
                                setup_progress= lambda total_imgs, x=chapter_download_task: self.setup_chapter_task_progress(x, total_imgs),
                                progress_notifier= lambda x=chapter_download_task: self.progress_chapter_download_task(x),
                                completion_notifier= lambda x=chapter_download_task: self.chapter_task_completion(x)
                            )
                        )
        self.progress.print(f'Successfully Downloaded [red]{n_chapters_to_download}[/] {"chapter" if n_chapters_to_download <= 1 else "chapters"} of [medium_spring_green]{self.series.series_title}[/] in [italic plum2]{os.path.abspath(dest)}[/].')

    def setup_chapter_task_progress(self, chapter_download_task_id: int, total_images: int):
        self.progress.update(chapter_download_task_id, total=total_images, rendered_total=total_images)
        self.progress.start_task(chapter_download_task_id)
    
    def chapter_task_completion(self, chapter_download_task_id: int):
        time.sleep(2)
        self.progress.remove_task(chapter_download_task_id)
    
    def progress_chapter_download_task(self, chapter_download_task_id: int, advance: int=1):
        self.progress.update(chapter_download_task_id, advance=advance)
    
    def submit_chapter_download_task(self, pool, **kwargs):
        return pool.submit(
            download_chapter, 
            logger=self.log,
            headers= self.session.image_headers,
            images_format=self.download_settings.images_format,
            **kwargs
        )

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

        self.log.info(f'Chapter {chapter_info.chapter_number} download complete with a total of {len(img_urls)} pages [green]✓')
        self.progress.remove_task(chapter_download_task_id)