import logging
import os
import pathlib
from WebtoonDownloader import logger
from WebtoonDownloader import WebtoonDownloader
from WebtoonDownloader.options import Options
from WebtoonDownloader.classes.DownloadSettings import DownloadSettings
from WebtoonDownloader.classes.progress.DownloadProgress import DownloadProgress
from WebtoonDownloader.classes.Series import Series

n_concurrent_chapters_download = 10
n_concurrent_images_download = 50

logger.configure_logger("INFO")
log = logging.getLogger(__name__)

def main():
    parser = Options()
    parser.initialize()
    try:
        args = parser.parse()
    except Exception as e:
        log.error(f'[red]Error:[/] {e}')
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
        series= Series("https://www.webtoons.com/en/slice-of-life/hello-world/list?title_no=827"), 
        download_settings= DownloadSettings(
            start=args.start,
            end=args.end,
            dest=args.dest,
            images_format=args.images_format,
            latest=args.latest,
            separate=separate,
            compress=compress_cbz,
            max_concurrent=n_concurrent_chapters_download,
            max_downloader_workers=n_concurrent_images_download
        ),
        log=log,
        progress = DownloadProgress()
    )
    # webtoon_downloader2 = WebtoonDownloader(
    #     series= Series("https://www.webtoons.com/en/action/omniscient-reader/list?title_no=2154"), 
    #     download_settings= DownloadSettings(
    #         start=args.start,
    #         end=args.end,
    #         dest=args.dest,
    #         images_format=args.images_format,
    #         latest=args.latest,
    #         separate=separate,
    #         compress=compress_cbz,
    #         max_concurrent=n_concurrent_chapters_download
    #     ),
    #     log=log,
    #     progress = DownloadProgress()
    # )
    webtoon_downloader.download()
    #webtoon_downloader2.download()

if(__name__ == '__main__'):
    main()