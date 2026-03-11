# Getting Started

This page walks through installation, the first successful download, and the flags most people need first.

## Requirements

- Python `3.10+`
- One of:
  - [`uv`](https://docs.astral.sh/uv/)
  - [`pipx`](https://pypa.github.io/pipx/)

## Install

### Option 1: `uv` Tool Install

```bash
uv tool install webtoon_downloader
```

### Option 2: `pipx`

```bash
pipx install webtoon_downloader
```

## Confirm The CLI Works

```bash
webtoon-downloader --help
```

If the command is not found, reopen your terminal and make sure your tool install directory is on `PATH`.

## Your First Download

Use a Webtoons series URL, not a single episode viewer URL:

```bash
webtoon-downloader "https://www.webtoons.com/en/.../list?title_no=..."
```

That command downloads the entire series into a folder named after the series title in your current working directory.

## Common First Commands

### Download Only The Latest Chapter

```bash
webtoon-downloader [url] --latest
```

### Download A Chapter Range

```bash
webtoon-downloader [url] --start 10 --end 25
```

### Save As CBZ

```bash
webtoon-downloader [url] --save-as cbz
```

### Save Under A Specific Folder

```bash
webtoon-downloader [url] --out ./downloads
```

### Export Metadata

```bash
webtoon-downloader [url] --export-metadata --export-format json
```

## Output Modes

The downloader supports four storage targets:

| Option   | Result                    |
| -------- | ------------------------- |
| `images` | One file per page on disk |
| `zip`    | One ZIP per chapter       |
| `cbz`    | One CBZ per chapter       |
| `pdf`    | One PDF per chapter       |

## Image Options

### Change The Image Format

```bash
webtoon-downloader [url] --image-format png
```

Supported values:

- `jpg`
- `png`

### Lower Image Quality

```bash
webtoon-downloader [url] --quality 50
```

Rules:

- minimum `40`
- maximum `100`
- steps of `10`

## Stability Settings

Webtoons can rate limit aggressive downloads. These flags are the first ones to tune when downloads get flaky.

### Lower Concurrency

```bash
webtoon-downloader [url] --concurrent-chapters 2 --concurrent-pages 5
```

### Use A Proxy

```bash
webtoon-downloader [url] --proxy http://127.0.0.1:7890
```

### Keep Retries Enabled

```bash
webtoon-downloader [url] --retry-strategy exponential
```

## When To Use `--debug`

If a download fails and you want useful diagnostics, rerun with:

```bash
webtoon-downloader [url] --debug
```

That enables richer console output and writes `webtoon_downloader.log`.

## Next Steps

- For the full option set, see the [CLI Guide](cli.md)
- For known limitations, see the [FAQ](faq.md)
- For implementation details, see the [Architecture](architecture.md)
