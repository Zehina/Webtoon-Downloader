import json

import pytest

from webtoon_downloader.core.webtoon.exporter import DataExporter


@pytest.mark.asyncio
async def test_add_series_summary_json_only_keeps_summary_in_info_json(tmp_path) -> None:
    exporter = DataExporter("json")
    summary = "Series summary should be exported in JSON mode"

    await exporter.add_series_summary(summary, tmp_path / "summary.txt")
    await exporter.write_data(tmp_path)

    info = json.loads((tmp_path / "info.json").read_text())
    assert info["summary"] == summary
    assert not (tmp_path / "summary.txt").exists()


@pytest.mark.asyncio
async def test_add_series_summary_text_writes_summary_txt(tmp_path) -> None:
    exporter = DataExporter("text")
    summary = "Text export should write summary.txt"

    await exporter.add_series_summary(summary, tmp_path / "summary.txt")

    assert (tmp_path / "summary.txt").read_text().strip() == summary
