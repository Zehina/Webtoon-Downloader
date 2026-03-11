# CLI Guide

This page documents the current command-line interface exposed by `webtoon-downloader`.

## Command Shape

```bash
webtoon-downloader [OPTIONS] URL
```

`URL` must be a Webtoons series page URL of the form:

```bash
https://www.webtoons.com/en/.../list?title_no=...
```

## Core Download Selection

### `--start`, `-s`

Start downloading from a specific chapter number.

```bash
webtoon-downloader [url] --start 10
```

### `--end`, `-e`

Stop downloading at a specific chapter number.

```bash
webtoon-downloader [url] --end 50
```

### `--latest`, `-l`

Download only the latest chapter.

```bash
webtoon-downloader [url] --latest
```

`--latest` cannot be combined with `--start` or `--end`.

## Output And Storage

### `--out`, `-o`

Set the parent output directory.

```bash
webtoon-downloader [url] --out ./downloads
```

### `--save-as`, `-sa`

Choose how each chapter is stored.

Supported values:

- `images`
- `zip`
- `cbz`
- `pdf`

Examples:

```bash
webtoon-downloader [url] --save-as images
webtoon-downloader [url] --save-as cbz
webtoon-downloader [url] --save-as pdf
```

### `--separate`

Store each chapter in its own folder when using image output.

```bash
webtoon-downloader [url] --save-as images --separate
```

This option is only valid with `--save-as images`.

## Image Options

### `--image-format`, `-f`

Convert downloaded images to a target format.

Supported values:

- `jpg`
- `png`

```bash
webtoon-downloader [url] --image-format png
```

### `--quality`

Request a lower Webtoons image quality setting.

```bash
webtoon-downloader [url] --quality 50
```

Valid values:

- `40`
- `50`
- `60`
- `70`
- `80`
- `90`
- `100`

## Metadata Export

### `--export-metadata`, `-em`

Export text metadata such as:

- series summary
- chapter titles
- author notes

```bash
webtoon-downloader [url] --export-metadata
```

### `--export-format`, `-ef`

Choose the metadata export format.

Supported values:

- `json`
- `text`
- `all`

```bash
webtoon-downloader [url] --export-metadata --export-format all
```

## Reliability And Networking

### `--retry-strategy`

Choose how failed requests are retried.

Supported values:

- `exponential`
- `linear`
- `fixed`
- `none`

```bash
webtoon-downloader [url] --retry-strategy exponential
```

Using `none` disables retries completely.

### `--concurrent-chapters`

Set the number of chapters downloaded concurrently.

Default: `6`

```bash
webtoon-downloader [url] --concurrent-chapters 2
```

### `--concurrent-pages`

Set the number of image downloads allowed in parallel.

Default: `120`

```bash
webtoon-downloader [url] --concurrent-pages 5
```

This limit is shared across all chapter downloads.

### `--proxy`

Send requests through an HTTP proxy.

```bash
webtoon-downloader [url] --proxy http://127.0.0.1:7890
```

## Diagnostics

### `--debug`

Enable debug logging and richer failure context.

```bash
webtoon-downloader [url] --debug
```

## Informational Flags

### `--version`

Show the installed CLI version.

### `--help`

Show the generated help text.

## Practical Examples

### Small, Safer Download Run

```bash
webtoon-downloader [url] --concurrent-chapters 2 --concurrent-pages 5 --retry-strategy exponential
```

### Archive-Friendly Output

```bash
webtoon-downloader [url] --save-as cbz --export-metadata --export-format json
```

### Debugging A Problematic Series

```bash
webtoon-downloader [url] --debug --retry-strategy fixed --concurrent-pages 3
```
