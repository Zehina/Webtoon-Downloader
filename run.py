import logging
import os
import pathlib
from WebtoonDownloader import logger
from WebtoonDownloader import WebtoonDownloader
from WebtoonDownloader.options import Options
from WebtoonDownloader.classes.DownloadSettings import DownloadSettings
from WebtoonDownloader.classes.progress.DownloadProgress import DownloadProgress
from WebtoonDownloader.classes.Series import Series

n_concurrent_chapters_download = 2
logger.configure_logger("DEBUG")
log = logging.getLogger(__name__)

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
    progress = DownloadProgress()
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