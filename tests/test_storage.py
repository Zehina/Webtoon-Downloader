from __future__ import annotations

import io
import os
import tempfile
import zipfile
from typing import AsyncIterator

import fitz
import pytest
from PIL import Image

from webtoon_downloader.storage import (
    AioFileBufferedZipWriter,
    AioPdfWriter,
    AioZipWriter,
)
from webtoon_downloader.storage.exceptions import StreamWriteError


async def async_iter_image(image: Image.Image, chunk_size: int = 1024) -> AsyncIterator[bytes]:
    with io.BytesIO() as output:
        image.save(output, format="JPEG")
        output.seek(0)
        data = output.read()
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]


async def async_iter(data: bytes, chunk_size: int = 1024) -> AsyncIterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


async def _test_zipwriter(file: str | os.PathLike | io.BytesIO, zip_writer: type[AioZipWriter]) -> None:
    test_files = [
        ("test.txt", b"Through Heaven and Earth, I Alone am the Honored One."),
        ("唯", "天上天下 唯我独尊".encode()),
        ("人都.者", "每个人都是自己健康或疾病的创作者".encode()),
    ]

    async with zip_writer(file, "w") as writer:
        for filename, data in test_files:
            await writer.write(async_iter(data), filename)

    if isinstance(file, io.BytesIO):
        # If file is an io.BytesIO object, reset the position
        file.seek(0)

    with zipfile.ZipFile(file, "r") as zip_ref:
        for filename, data in test_files:
            with zip_ref.open(filename, "r") as f:
                assert data == f.read()


@pytest.mark.asyncio
async def test_pdf_writer() -> None:
    # Create test images
    test_images = [
        Image.new("RGB", (100, 100), color="red"),
        Image.new("RGB", (200, 200), color="green"),
        Image.new("RGB", (300, 300), color="blue"),
    ]

    with tempfile.NamedTemporaryFile(prefix="test_pdf", suffix=".pdf") as f:
        async with AioPdfWriter(f) as writer:
            for idx, img in enumerate(test_images):
                await writer.write(async_iter_image(img), f"image_{idx}.jpg")

        with fitz.open(f) as doc:
            assert len(doc) == len(test_images)  # Check number of pages

            for page_num, img in enumerate(test_images):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()  # pyright: ignore[reportAttributeAccessIssue]
                assert pix.width == img.width and pix.height == img.height


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zip_writer",
    [
        AioZipWriter,
        AioFileBufferedZipWriter,
    ],
)
async def test_zipwriter_buffer(zip_writer: type[AioZipWriter]) -> None:
    await _test_zipwriter(io.BytesIO(), zip_writer)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zip_writer",
    [
        AioZipWriter,
        AioFileBufferedZipWriter,
    ],
)
async def test_zipwriter_file(zip_writer: type[AioZipWriter]) -> None:
    with tempfile.NamedTemporaryFile(prefix="test_storage", suffix=".zip") as f:
        await _test_zipwriter(f.name, zip_writer)


@pytest.mark.asyncio
async def test_write_raises_stream_write_error() -> None:
    async with AioZipWriter(io.BytesIO()) as writer:
        with pytest.raises(StreamWriteError):
            # Passing an invalid file name
            await writer.write(async_iter(b"some data"), 12)

    with pytest.raises(StreamWriteError), tempfile.TemporaryDirectory() as dir_path:
        # Openning a directory should cause an error
        async with AioZipWriter(dir_path) as writer:
            await writer.write(async_iter(b"some data"), "test.txt")
