from __future__ import annotations

import io
from dataclasses import dataclass, field
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import IO, AsyncIterator, NamedTuple

import fitz
from PIL import Image

from .exceptions import stream_error_handler


class ImageDimension(NamedTuple):
    """
    Represents the dimensions of an image.

    Args:
        width   : The width of the image.
        height  : The height of the image.
    """

    width: int
    height: int


class PageData(NamedTuple):
    """
    Represents the data for a page to be added to a PDF.

    Args:
        name        : The name of the page.
        stream      : The stream of image bytes.
        dimension   : The dimensions of the image.
    """

    name: str
    stream: BytesIO
    dimension: ImageDimension


@dataclass
class AioPdfWriter:
    """
    Asynchronous writer for creating PDFs from image streams.

    Args:
        container: The BytesIO or PathLike object where the PDF will be written.
    """

    container: io.BytesIO | IO[bytes] | PathLike[str]

    _doc: fitz.Document = field(init=False)
    _pages_data: list[PageData] = field(init=False)

    @stream_error_handler
    async def __aenter__(self) -> AioPdfWriter:
        if isinstance(self.container, (str, PathLike)):
            Path(self.container).parent.mkdir(parents=True, exist_ok=True)
        self._pages_data = []
        self._doc = fitz.open()
        return self

    @stream_error_handler
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        """
        Writes an asynchronous byte stream to a PDF file.

        Args:
            stream      : The asynchronous byte stream to write.
            item_name   : The item name is only used for sorting the pages that are added to the PDF document.

        Returns:
            The total number of bytes written to the file.
        """
        bytes_io_stream = BytesIO()
        written = 0
        async for chunk in stream:
            bytes_io_stream.write(chunk)
            written += len(chunk)
        bytes_io_stream.seek(0)

        # Determine image size
        with Image.open(bytes_io_stream) as img:
            img_width, img_height = img.size

        # Reset stream position after reading
        bytes_io_stream.seek(0)

        # Store the image stream along with its item name and size
        self._pages_data.append(
            PageData(
                name=item_name,
                stream=bytes_io_stream,
                dimension=ImageDimension(width=img_width, height=img_height),
            )
        )
        return written

    @stream_error_handler
    async def __aexit__(self, *_: tuple) -> None:
        """
        Completes the PDF creation process by adding pages sorted by item name.
        """
        # Sort the stored page data by item name
        self._pages_data.sort(key=lambda x: x[0])
        # Add each image to the PDF
        for page in self._pages_data:
            self._add_image_to_pdf(page)

        if self._doc.page_count > 0:
            self._doc.save(self.container)
        self._doc.close()

    def _add_image_to_pdf(self, page_data: PageData) -> None:
        """
        Adds an image using its original size to the PDF document.

        Args:
            page_data: The data of the page to be added.
        """
        page = self._doc.new_page(-1, width=page_data.dimension.width, height=page_data.dimension.height)  # pyright: ignore[reportAttributeAccessIssue]

        page.insert_image(
            fitz.Rect(0, 0, page_data.dimension.width, page_data.dimension.height),
            stream=page_data.stream,
        )
