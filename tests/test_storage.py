import io
import os
import tempfile
import zipfile

import pytest

from webtoon_downloader.storage import AioFileBufferedZipWriter, AioZipWriter


async def async_iter(data: bytes, chunk_size: int = 1024):
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


async def _test_zipwriter(file: str | os.PathLike | io.BytesIO, zip_writer: AioZipWriter):
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
            with zip_ref.open(filename, "r") as file:
                assert data == file.read()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zip_writer",
    [
        AioZipWriter,
        AioFileBufferedZipWriter,
    ],
)
async def test_zipwriter_buffer(zip_writer: AioZipWriter):
    await _test_zipwriter(io.BytesIO(), zip_writer)


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zip_writer",
    [
        AioZipWriter,
        AioFileBufferedZipWriter,
    ],
)
async def test_zipwriter_file(zip_writer: AioZipWriter):
    with tempfile.NamedTemporaryFile(prefix="test_storage", suffix=".zip") as f:
        await _test_zipwriter(f.name, zip_writer)
