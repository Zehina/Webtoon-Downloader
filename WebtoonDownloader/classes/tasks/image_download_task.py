import requests
import os
import shutil
from PIL import Image
from typing import Callable

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
    r = requests.get(url, headers=headers, stream=True)
    progress_notifier()

    if r.status_code == 200:
        r.raw.decode_content = True
        downloaded_image_path = os.path.join(dest, f'{file_name}.{image_format}')
        if(image_format == 'png'):
            Image.open(r.raw).save(downloaded_image_path)
        else:
            with open(downloaded_image_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        return file_name
    else:
        if logger:
            logger.error(f'[bold red blink]Unable to download page[/] [medium_spring_green]{page_number}[/]' 
                    f'from chapter [medium_spring_green]{chapter_number}[/], request returned' 
                    f'error [bold red blink]{r.status_code}[/]')