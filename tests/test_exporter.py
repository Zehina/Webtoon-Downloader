import json

import pytest

from webtoon_downloader.core.webtoon.exporter import DataExporter
from webtoon_downloader.core.webtoon.models import ChapterInfo


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


@pytest.mark.asyncio
async def test_text_export_writes_unicode_as_utf8(tmp_path) -> None:
    exporter = DataExporter("all")
    chapter = ChapterInfo(
        number=27,
        viewer_url="https://www.webtoons.com/viewer",
        data_episode_no=27,
        title="Afterword ˘ Sequel",
        series_title="Reunion",
        total_chapters=27,
    )
    notes = "Creator notes with ˘"

    await exporter.add_chapter_details(chapter, tmp_path / "title.txt", tmp_path / "notes.txt", notes)
    await exporter.write_data(tmp_path)

    assert (tmp_path / "title.txt").read_text(encoding="utf-8").strip() == chapter.title
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8").strip() == notes
    assert "Afterword ˘ Sequel" in (tmp_path / "info.json").read_text(encoding="utf-8")
