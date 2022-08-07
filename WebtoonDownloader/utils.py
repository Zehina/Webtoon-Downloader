import concurrent
import requests
import os
import shutil
from io import BytesIO
from PIL import Image
from typing import Callable
from WebtoonDownloader.classes.threads.ThreadPoolExecutorWithQueueSizeLimit import ThreadPoolExecutorWithQueueSizeLimit
import aiohttp
import asyncio

def download_chapter(setup_progress: Callable, progress_notifier: Callable, completion_notifier: Callable, image_extractor: Callable, chapter_info, dest: str, headers: dict, max_img_download_workers: int, images_format: str='jpg', compress_cbz=False, logger=None):
    """
    downloads pages starting of a given chapter, inclusive.
    stores the downloaded images into the dest path.

    Arguments:
    ----------
    
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
    print(f'initiating {max_img_download_workers} workers')
    #asyncio.run(download)
    with ThreadPoolExecutorWithQueueSizeLimit(maxsize=max_img_download_workers) as pool:
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
            concurrent.futures.wait(image_download_futures, return_when=concurrent.futures.ALL_COMPLETED)
            for future in image_download_futures:
                try:
                    r = future.result()
                except BaseException as e:
                    print(f"failed with {e}")
            # if self.done_event.is_set():
            #     return
        try:
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    def x(img_data, path):
                        with Image.open(img_data) as image:
                            return executor.submit(save_image, image, path, images_format)
                futu = []
                for fut in image_download_futures:
                    img_path, raw_data, page_number =fut.result()
                    futu.append(x(raw_data,img_path))
                #futures = [x(fut.result() for fut in image_download_futures) for fut in futures]
            except Exception as ex:
                print(f"Exception: {ex}")
        except BaseException as e:
            logger.info(f'Chapter {chapter_info.chapter_number} error {e}')
        if compress_cbz:
            self.log.info('cbz enabled')
            with zipfile.ZipFile(f'{dest}.cbz', 'w') as cbz_zip:
                for future in image_download_futures:
                    image_file_path = future.result()
                    image_folder, image_file_name = os.path.split(image_file_path)
                    cbz_zip.write(image_file_path, compress_type=zipfile.ZIP_STORED, arcname=image_file_name)
    if logger:
        logger.info(f'Chapter {chapter_info.chapter_number} download complete with a total of {len(img_urls)} pages [green]✓')
    completion_notifier()

def save_image(img, path, images_format):
    print('HELOOOOOOOO')
    img.save(path, format=images_format)
    return path

def download_image(progress_notifier: Callable, url: str, dest: str, chapter_number: int, page_number: int, file_name: str, headers, image_format:str='jpg', logger=None):
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
    image_format: str
        format of downloaded image.
        (default: jpg)
    """
    if logger:
        logger.debug(f"Requesting chapter {chapter_number}: page {page_number}")
    with requests.get(url, headers=headers, stream=True) as r:
        progress_notifier()

        if r.status_code == 200:
            try:
                # r.raw.decode_content = True
                downloaded_image_path = os.path.join(dest, f'{file_name}.{image_format}')
                # if(image_format == 'png'):
                # try:
                with Image.open(r.raw) as img:
                    if img.mode in ["RGBA", "P"] and image_format in ["jpg", "jpeg"]:
                        img = img.convert('RGB')
                    # if img.mode != 'RGB' and image_format in ["jpg", "jpeg"]:
                #             img = img.convert('RGB')
                    img.save(os.path.join(dest, f'{file_name}.{image_format}'))
                # except BaseException as e:
                #     logger.error(e)
                #     raise e
                # with open(downloaded_image_path, 'wb') as f:
                #     shutil.copyfileobj(r.raw, f)
                return downloaded_image_path, r.raw, page_number
            except Exception as e:
                print('xdddddddd')
                logger.error(f"page {page_number} errored with {e}")
        else:
            if logger:
                logger.error(
                        f'[bold red blink]Unable to download page [/][medium_spring_green]{page_number}[/] ' 
                        f'from chapter [medium_spring_green]{chapter_number}[/], request returned ' 
                        f'error [bold red blink]{r.status_code}[/]'
                    )