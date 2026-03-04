from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True)
class SeriesMetadata:
    title: str
    summary: str | None = None
    author: str | None = None
    genre: str | None = None
    language: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ComicInfoMetadata:
    series: str
    title: str | None = None
    number: str | None = None
    count: int | None = None
    summary: str | None = None
    notes: str | None = None
    year: int | None = None
    month: int | None = None
    day: int | None = None
    writer: str | None = None
    genre: str | None = None
    language_iso: str | None = None
    page_count: int | None = None
    manga: str | None = None
    web: str | None = None


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def build_comicinfo_xml(metadata: ComicInfoMetadata) -> bytes:
    root = ET.Element("ComicInfo")

    fields: list[tuple[str, object]] = [
        ("Title", metadata.title),
        ("Series", metadata.series),
        ("Number", metadata.number),
        ("Count", metadata.count),
        ("Summary", metadata.summary),
        ("Notes", metadata.notes),
        ("Year", metadata.year),
        ("Month", metadata.month),
        ("Day", metadata.day),
        ("Writer", metadata.writer),
        ("Genre", metadata.genre),
        ("LanguageISO", metadata.language_iso),
        ("PageCount", metadata.page_count),
        ("Manga", metadata.manga),
        ("Web", metadata.web),
    ]

    for key, value in fields:
        if not _has_value(value):
            continue
        node = ET.SubElement(root, key)
        node.text = str(value)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    return cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=True))
