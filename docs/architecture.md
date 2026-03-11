# Architecture

This page describes how the downloader is structured internally and how a request flows through the project.

## High-Level Flow

The normal flow is:

1. The CLI parses arguments and builds `WebtoonDownloadOptions`.
2. `download_webtoon()` wires together the client, fetcher, transformers, storage, and exporters.
3. `WebtoonFetcher` resolves the series and chapter list.
4. `WebtoonDownloader` orchestrates chapter tasks.
5. `ChapterDownloader` fetches chapter viewer pages and schedules page downloads.
6. `HttpImageDownloader` streams image bytes.
7. Storage writers persist the result as files, ZIPs, CBZs, or PDFs.

## Main Components

| Area                                                     | Responsibility                                         |
| -------------------------------------------------------- | ------------------------------------------------------ |
| `webtoon_downloader/cmd`                                 | CLI, option validation, progress UI                    |
| `webtoon_downloader/core/webtoon/client.py`              | HTTP client, headers, retry transport, image streaming |
| `webtoon_downloader/core/webtoon/fetchers.py`            | Series lookup and chapter enumeration                  |
| `webtoon_downloader/core/webtoon/downloaders/comic.py`   | Top-level orchestration for a whole series             |
| `webtoon_downloader/core/webtoon/downloaders/chapter.py` | Per-chapter workflow and page scheduling               |
| `webtoon_downloader/core/downloaders/image.py`           | Image streaming and transformer pipeline               |
| `webtoon_downloader/storage`                             | Folder, ZIP, and PDF output writers                    |
| `webtoon_downloader/transformers`                        | Image format conversion and byte-stream mutation       |

## CLI Layer

The CLI lives in `webtoon_downloader/cmd/cli.py`.

It is responsible for:

- parsing options
- validating combinations such as `--latest` vs `--start`/`--end`
- setting up the event loop
- wiring progress callbacks
- presenting user-facing errors

This layer should remain thin. Most business logic belongs in the core modules, not inside click handlers.

## HTTP Layer

`WebtoonHttpClient` centralizes request behavior:

- connection pooling
- request headers and user-agent selection
- mobile vs standard Webtoons domain handling
- retry transport selection
- explicit request and image-stream timeouts

The image path uses `stream_image()` because image downloads have different requirements from metadata or page fetches.

## Fetching Chapters

`WebtoonFetcher` converts the series URL to the mobile domain, extracts the `title_no`, and uses the Webtoons API to retrieve episode metadata.

The fetcher constructs normalized `ChapterInfo` records used throughout the rest of the pipeline.

## Series Orchestration

`WebtoonDownloader` is the top-level coordinator for a download run.

It handles:

- resolving the chapter list
- determining the output directory
- preparing optional export data
- choosing the correct storage writer per chapter
- spawning chapter tasks

This is the right place to look when changing run-level behavior.

## Chapter Orchestration

`ChapterDownloader` handles one chapter at a time:

- fetch the viewer page
- extract image URLs and chapter notes
- export metadata if enabled
- schedule page downloads
- write `ComicInfo.xml` for CBZ output when applicable

It owns chapter-level concurrency through an internal semaphore.

## Image Pipeline

`HttpImageDownloader` is the leaf downloader:

- opens the image stream
- applies optional transformers
- writes the byte stream to the selected storage backend
- reports per-page progress

This layer is where request failures become `ImageDownloadError`.

## Storage Backends

The `storage` package defines asynchronous writers for different output targets:

- `AioFolderWriter`
- `AioZipWriter`
- `AioPdfWriter`

All of them implement the same `AioWriter` protocol so the rest of the pipeline can stay storage-agnostic.

## Export And Metadata

Metadata export is handled separately from image storage:

- text and JSON exports go through `DataExporter`
- CBZ metadata uses ComicInfo XML helpers in `comicinfo.py`

This separation keeps archive writing and metadata writing from being tightly coupled.

## Error Model

The project uses layered exceptions so failures stay readable:

- `WebtoonDownloadError`
- `ChapterDownloadError`
- `ImageDownloadError`
- specialized fetch and rate-limit errors

The CLI unwraps that chain to show compact summaries while still preserving root causes.

## Extension Points

If you want to extend the project, the safest entry points are:

- new storage writers under `storage/`
- new image transformers under `transformers/`
- exporter format improvements in `exporter.py`
- fetcher/parser updates when Webtoons changes upstream behavior
