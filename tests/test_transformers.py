import io

import pytest
from PIL import Image

from webtoon_downloader.transformers.image import (
    AioImageFormatTransformer,
    ImageFormat,
    _bytesio_to_async_gen,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "original_format, target_format, mode",
    [
        ("PNG", "JPEG", "RGB"),
        ("PNG", "PNG", "RGB"),
        ("JPEG", "PNG", "RGB"),
        ("JPEG", "JPEG", "RGB"),
        ("PNG", "JPEG", "P"),
        ("PNG", "PNG", "P"),
    ],
)
async def test_image_format_transformer(original_format: str, target_format: ImageFormat, mode: str) -> None:
    # Create a sample image in memory
    original_image = Image.new(mode, (100, 100), color="red")
    original_stream = io.BytesIO()
    original_image.save(original_stream, format=original_format)
    original_stream.seek(0)

    # Convert BytesIO to async iterator
    async_image_stream = _bytesio_to_async_gen(original_stream)

    # Transform image to PNG
    transformer = AioImageFormatTransformer(target_format)
    transformed_stream, _ = await transformer.transform(async_image_stream, "test")

    # Verify transformation
    transformed_bytes_io = io.BytesIO()
    async for chunk in transformed_stream:
        transformed_bytes_io.write(chunk)
    transformed_bytes_io.seek(0)
    transformed_image = Image.open(transformed_bytes_io)

    assert transformed_image.format == target_format

    # Check if the transformation was skipped for same format
    if original_format.upper() == target_format.upper():
        original_stream.seek(0)
        transformed_bytes_io.seek(0)
        assert (
            original_stream.read() == transformed_bytes_io.read()
        ), "Transformation should be skipped for same formats"
