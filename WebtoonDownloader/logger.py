import logging
from rich.console import Console
from rich.logging import RichHandler

def configure_logger(level: str= "INFO", file_name: str= 'webtoon_downloader.log'):
    console = Console()
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    FORMAT = "%(message)s"
    LOG_FILENAME = file_name

    logging.basicConfig(
        level=level, format=FORMAT, datefmt="[%X]", 
        handlers=[RichHandler(
            rich_tracebacks=True, 
            tracebacks_show_locals= True, 
            markup=True
        )]
    )