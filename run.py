import logging
import os
import pathlib
from rich.console import Console
from rich.logging import RichHandler
from WebtoonDownloader import WebtoonDownloader
from WebtoonDownloader.options import Options
from WebtoonDownloader.classes.DownloadSettings import DownloadSettings
from WebtoonDownloader.classes.progress.DownloadProgress import DownloadProgress
from WebtoonDownloader.classes.Series import Series

######################## Log Configuration ################################
console = Console()
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
log = logging.getLogger(__name__)
FORMAT = "%(message)s"
LOG_FILENAME = 'webtoon_downloader.log'
progress = DownloadProgress()

logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", 
    handlers=[RichHandler(
        rich_tracebacks=True, 
        tracebacks_show_locals= True, 
        markup=True
    )]
)
###########################################################################

n_concurrent_chapters_download = 2

def main():
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
    separate = args.seperate or args.separate
    compress_cbz = args.cbz and separate
    webtoon_downloader = WebtoonDownloader(
        series= Series(series_url), 
        download_settings= DownloadSettings(
            start=args.start,
            end=args.end,
            dest=args.dest,
            images_format=args.images_format,
            latest=args.latest,
            separate=separate,
            compress=compress_cbz,
            max_concurrent=n_concurrent_chapters_download
        ),
        log=log,
        progress = progress
    )
    webtoon_downloader.download()

if(__name__ == '__main__'):
    main()