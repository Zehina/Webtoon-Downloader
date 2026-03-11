<!-- PROJECT LOGO -->
<br />
<p align="center">

  <h2 align="center">Webtoon Downloader</h2>

  <p align="center">
    A fast CLI for downloading chapters from Webtoons. ⚡📚
    <br />
    <br />
    <a href="https://github.com/Zehina/Webtoon-Downloader/issues">Report Bug</a>
    ·
    <a href="https://github.com/Zehina/Webtoon-Downloader/issues">Request Feature</a>
  </p>
</p>

[![Release](https://img.shields.io/github/v/release/Zehina/webtoon-downloader)](https://github.com/Zehina/Webtoon-Downloader/releases)
[![Build status](https://img.shields.io/github/actions/workflow/status/Zehina/webtoon-downloader/main.yml?branch=master)](https://github.com/Zehina/webtoon-downloader/actions/workflows/main.yml?query=branch%3Amaster)
[![Commit activity](https://img.shields.io/github/commit-activity/m/Zehina/webtoon-downloader)](https://img.shields.io/github/commit-activity/m/Zehina/webtoon-downloader)
[![License](https://img.shields.io/github/license/Zehina/webtoon-downloader)](https://img.shields.io/github/license/Zehina/webtoon-downloader)

<p align="center">
  <img src="https://raw.githubusercontent.com/Zehina/Webtoon-Downloader/da001b7f9198a842610e09d3e45a31b0f5e0b9e9/docs/imgs/demo.svg">
</p>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary><h2 style="display: inline-block">Contents</h2></summary>
  <ol>
    <li><a href="#supported-sites">Supported Sites</a></li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#compatibility">Compatibility</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#faq">FAQ</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#built-with">Built With</a></li>
  </ol>
</details>

## Supported Sites 🌐

- [https://www.webtoons.com/](https://www.webtoons.com/)

## Disclaimer ⚠️

This tool is intended for personal and educational use only. You are responsible for how you use it, including compliance with the terms of service of the websites involved.

## Getting Started 🚀

Install the CLI, grab a series URL, and start downloading.

<p align="center">
  <img src="https://github.com/Zehina/Webtoon-Downloader/blob/master/docs/imgs/help.png?raw=true">
</p>

### Compatibility 🖥️

Webtoon Downloader runs on **Windows**, **Linux**, and **macOS**. Requires **Python 3.10+**.

### Installation 📦

Install via `uv` (recommended):

```bash
uv tool install webtoon_downloader
```

Or install via `pipx`:

```bash
pipx install webtoon_downloader
```

---

## Usage 🛠️

Pass a Webtoons series URL in the form:

```bash
webtoon-downloader "https://www.webtoons.com/en/.../list?title_no=..."
```

Run `webtoon-downloader --help` to see the full CLI help text.

### Basic Examples ✨

- Download all chapters:

  ```bash
  webtoon-downloader "https://www.webtoons.com/en/.../list?title_no=..."
  ```

- Download from chapter 10 to the end:

  ```bash
  webtoon-downloader [url] --start 10
  ```

- Download through chapter 150:

  ```bash
  webtoon-downloader [url] --end 150
  ```

- Download a specific range (inclusive):

  ```bash
  webtoon-downloader [url] --start 35 --end 67
  ```

- Download only the **latest released** chapter:

  ```bash
  webtoon-downloader [url] --latest
  ```

### Output And Storage 💾

- Save chapters as images, `zip`, `cbz`, or `pdf`:

  ```bash
  webtoon-downloader [url] --save-as cbz
  ```

- Store downloads under a custom parent directory:

  ```bash
  webtoon-downloader [url] --out ./downloads
  ```

- Save each chapter in its own folder:

  ```bash
  webtoon-downloader [url] --separate
  ```

  `--separate` is only valid when `--save-as images` is used.

- Change the output image format:

  ```bash
  webtoon-downloader [url] --image-format png
  ```

### Metadata Export 📝

- Export series and chapter metadata:

  ```bash
  webtoon-downloader [url] --export-metadata
  ```

- Choose the export format:

  ```bash
  webtoon-downloader [url] --export-metadata --export-format all
  ```

  Supported values: `json`, `text`, `all`.

### Common Command Examples 🎯

- Download to a specific folder and keep chapters as separate image folders:

  ```bash
  webtoon-downloader [url] --out ./downloads --separate
  ```

- Save each chapter as a CBZ archive:

  ```bash
  webtoon-downloader [url] --save-as cbz
  ```

- Export metadata alongside the download:

  ```bash
  webtoon-downloader [url] --export-metadata --export-format json
  ```

- Use a proxy and lower concurrency to reduce rate limiting:

  ```bash
  webtoon-downloader [url] --proxy http://127.0.0.1:7890 --concurrent-chapters 2 --concurrent-pages 5
  ```

- Disable retries completely:

  ```bash
  webtoon-downloader [url] --retry-strategy none
  ```

- Enable debug logging for troubleshooting:

  ```bash
  webtoon-downloader [url] --debug
  ```

### Networking And Reliability 🌐

Downloading a large number of chapters in a short time can trigger rate limits or slow responses from Webtoons. These flags are the main controls for keeping things stable:

- Retry failed requests with a configurable strategy:

  ```bash
  webtoon-downloader [url] --retry-strategy exponential
  ```

  Supported values: `exponential`, `linear`, `fixed`, `none`.

- Lower concurrency if you hit rate limits:

  ```bash
  webtoon-downloader [url] --concurrent-chapters 2 --concurrent-pages 5
  ```

  Current defaults:

  - `--concurrent-chapters`: `6`
  - `--concurrent-pages`: `120`

- Use a proxy for requests:

  ```bash
  webtoon-downloader [url] --proxy http://127.0.0.1:7890
  ```

### Image Quality 🖼️

- Download smaller images by lowering the requested quality:

  ```bash
  webtoon-downloader [url] --quality 50
  ```

  `--quality` must be between `40` and `100`, in steps of `10`.

### Debugging 🐞

- Enable debug logging:

  ```bash
  webtoon-downloader [url] --debug
  ```

### Output Example 📂

By default, downloads are stored in the current working directory under a folder named after the series title.

Example layout for `--save-as images`:

```text
Tower_of_God
├── 150_001.jpg
├── 150_002.jpg
├── 150_003.jpg
└── ...
```

With `--separate`, the structure becomes:

```text
Tower_of_God
├── 150
│   ├── 150_001.jpg
│   ├── 150_002.jpg
│   └── ...
├── 151
│   ├── 151_001.jpg
│   └── ...
└── 152
    ├── 152_001.jpg
    └── ...
```

### CLI Reference 📚

Current options exposed by the CLI:

- `--start`, `-s`: start downloading at a specific chapter number.
- `--end`, `-e`: stop downloading at a specific chapter number.
- `--latest`, `-l`: download only the latest chapter.
- `--export-metadata`, `-em`: export series summary, chapter names, and author notes.
- `--export-format`, `-ef`: choose `json`, `text`, or `all` for metadata export output.
- `--image-format`, `-f`: choose `jpg` or `png` for downloaded images.
- `--out`, `-o`: set the parent download directory.
- `--save-as`, `-sa`: choose `images`, `zip`, `cbz`, or `pdf`.
- `--separate`: place each chapter in its own folder when saving as images.
- `--concurrent-chapters`: set the chapter download worker count.
- `--concurrent-pages`: set the image download worker count.
- `--proxy`: route requests through an HTTP proxy.
- `--retry-strategy`: choose `exponential`, `linear`, `fixed`, or `none`.
- `--quality`: request image quality from `40` to `100`, in steps of `10`.
- `--debug`: enable debug logging.
- `--version`: print the installed CLI version.
- `--help`: show the generated help text.

---

## FAQ 🙋

### Why do I get rate limited, timeouts, or incomplete downloads? 😵

This usually comes from Webtoons or its image CDN slowing down or rejecting bursts of requests. The downloader cannot bypass remote rate limits on its own.

Try:

- lowering `--concurrent-chapters` and `--concurrent-pages`
- keeping `--retry-strategy` enabled
- using `--proxy` if your network or region is being throttled
- retrying later if Webtoons is unstable

This has shown up repeatedly in issue reports such as slow image downloads and recurring request failures.

### Can this download Daily Pass or app-only chapters? 🔒

No, not reliably. Chapters that are only exposed through the official app or gated behind Daily Pass are outside the normal website flow this project targets.

This is a platform limitation, not just a missing flag.

### Why does a series suddenly stop working even though it used to work? 🧩

Webtoons changes its HTML, viewer structure, and localized page layouts from time to time. When that happens, scraping logic can break until the project is updated.

If a series fails with parsing errors such as missing elements or missing titles, check the issue tracker first and open a new bug report with the failing URL and `--debug` output if needed.

### Why does the displayed chapter number not match `episode_no` in the URL? 🔢

Webtoons sometimes exposes a URL episode number that differs from the chapter numbering shown in the series UI. The downloader currently follows the chapter numbering it extracts from the site, not arbitrary RSS or URL numbering.

### Why does `webtoon-downloader` or `pip` say `command not found`? 🛤️

That is usually an installation or PATH problem on the local machine, not a downloader bug.

Typical fixes:

- install with `uv tool install webtoon_downloader` or `pipx install webtoon_downloader`
- reopen your terminal after installation
- make sure the tool install directory is on your PATH
- verify with `webtoon-downloader --version`

### Can the project prevent every download failure automatically? 🤷

No. Some failures are outside the project’s control:

- Webtoons rate limiting or temporary CDN instability
- app-only or Daily Pass content
- upstream site markup changes
- local proxy, PATH, Python, or package installation problems

The goal is to handle common failures well, but some classes of issues still require retrying later, changing settings, or waiting for a code update.

---

## Contributing 🤝

Contributions are welcome.

1. Fork the repo
2. Create a branch (`git checkout -b feature/new-idea`)
3. Commit changes (`git commit -m 'Add new idea'`)
4. Push to GitHub (`git push origin feature/new-idea`)
5. Create a pull request

---

## License 📄

Distributed under the MIT License. See `LICENSE` for more.

---

## Contact 📬

**Zehina** – [zehinadev@gmail.com](mailto:zehinadev@gmail.com)
[Project homepage](https://github.com/Zehina/Webtoon-Downloader)

---

## Built With 🧱

- [Rich](https://github.com/Textualize/rich) — Beautiful terminal formatting
- [Webtoons](https://www.webtoons.com/) — Source platform supported by this downloader.
- Many other libraries and tools used in this project can be found in the [pyproject.toml](https://github.com/Zehina/Webtoon-Downloader/blob/master/pyproject.toml) file.
