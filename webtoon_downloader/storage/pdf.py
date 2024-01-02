from __future__ import annotations

import io
from dataclasses import dataclass, field
from io import BytesIO
from os import PathLike
from typing import AsyncIterator, NamedTuple

import fitz
from PIL import Image


class ImageDimension(NamedTuple):
    width: int
    height: int


class PageData(NamedTuple):
    name: str
    stream: BytesIO
    dimension: ImageDimension


@dataclass
class AioPdfWriter:
    container: io.BytesIO | PathLike[str]

    _doc: fitz.Document = field(init=False)
    _pages_data: list[PageData] = field(init=False)

    async def __aenter__(self) -> AioPdfWriter:
        self._pages_data = []
        self._doc = fitz.open()
        return self

    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        bytes_io_stream = BytesIO()
        written = 0
        async for chunk in stream:
            bytes_io_stream.write(chunk)
            written += len(chunk)
        bytes_io_stream.seek(0)

        # Determine image size using PIL
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
        # Create a new PDF page with the size of the image
        page = self._doc.new_page(
            -1, width=page_data.dimension.width, height=page_data.dimension.height
        )

        # Insert the image into the page using its original size
        page.insert_image(
            fitz.Rect(0, 0, page_data.dimension.width, page_data.dimension.height),
            stream=page_data.stream,
        )
