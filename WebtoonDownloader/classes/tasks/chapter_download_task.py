import concurrent
import os
from typing import Callable
from WebtoonDownloader.classes.tasks.image_download_task import download_image
from WebtoonDownloader.classes.threads.ThreadPoolExecutorWithQueueSizeLimit import ThreadPoolExecutorWithQueueSizeLimit

def download_chapter(chapter_download_task_id: int, progress_notifier: Callable, setup_progress: Callable, image_extractor: Callable, chapter_info, dest: str, headers, images_format: str='jpg', compress_cbz=False, logger=None):
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

    if logger:
        logger.debug(f'[italic red]Accessing[/italic red] chapter {chapter_info}')
    img_urls = image_extractor()
    if not os.path.exists(dest):
        os.makedirs(dest)
    setup_progress(len(img_urls))
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=10, max_workers=4) as pool:
        image_download_futures = set()
        for page_number, url in enumerate(img_urls):
            image_download_futures.add(
                pool.submit(
                    download_image,
                    progress_notifier= progress_notifier,
                    url=url, 
                    dest=dest,
                    chapter_number = chapter_info.chapter_number,
                    page_number = page_number,
                    file_name=f"{chapter_info.chapter_number}_{page_number}", 
                    headers=headers,
                    image_format=images_format,
                    logger=logger
                )
            )
            # if self.done_event.is_set():
            #     return

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
    