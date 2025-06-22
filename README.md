<!-- PROJECT LOGO -->
<br />
<p align="center">

  <h2 align="center">Webtoon Downloader</h2>

  <p align="cen">
    A simple blazing fast tool for downloading chapters of any releases hosted on the webtoons website.⚡
    <br />
    <br />
    <a href="https://github.com/Zehina/Webtoon-Downloader/issues">Report Bug</a>
    ·
    <a href="https://github.com/Zehina/Webtoon-Downloader/issues">Request Feature</a>
  </p>
</p>

[![Release](https://img.shields.io/github/v/release/Zehina/webtoon-downloader)](https://img.shields.io/github/v/release/Zehina/webtoon-downloader)
[![Build status](https://img.shields.io/github/actions/workflow/status/Zehina/webtoon-downloader/main.yml?branch=main)](https://github.com/Zehina/webtoon-downloader/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/Zehina/webtoon-downloader/branch/main/graph/badge.svg)](https://codecov.io/gh/Zehina/webtoon-downloader)
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
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#built-with">Built With</a></li>
  </ol>
</details>

## Supported Sites

- [https://www.webtoons.com/](https://www.webtoons.com/)

## Disclaimer

This tool is intended for personal use and educational purposes only. By using it, you agree that you are solely responsible for how you use the software. I am not liable for any misuse, abuse, or violation of terms of service of the websites involved.

## Getting Started

To get a local copy up and running follow these simple steps.

<p align="center">
  <img src="https://github.com/Zehina/Webtoon-Downloader/blob/master/docs/imgs/help.png?raw=true">
</p>

### Compatibility

Webtoon Downloader runs on **Windows**, **Linux**, and **macOS**. Requires **Python 3.10+**.

### Installation

Install via `pipx` (recommended):

```bash
pipx install webtoon_downloader
```

---

## Usage

> Run `webtoon-downloader --help` for full options.

### Basic Examples

- Download **all chapters** of a series:

  ```bash
  webtoon-downloader "https://www.webtoons.com/en/.../list?title_no=..."
  ```

- Download from **chapter 10 to the end**:

  ```bash
  webtoon-downloader [url] --start 10
  ```

- Download up to **chapter 150**:

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

### Customization

#### Rate Limiting & Stability

Downloading a large number of chapters in quick succession can trigger rate limits from Webtoons' servers. If you experience timeouts or missing content, you can mitigate this using the following options:

- **Retry strategy**: determines how retries are handled when a request fails. By default, the tool uses `exponential` backoff.

  ```bash
  webtoon-downloader [url] --retry-strategy exponential
  ```

  Available values: `exponential`, `linear`, `fixed`

- **Concurrency settings**: tune how many workers download in parallel. By default:

  - `--concurrent-chapters` = `6`
  - `--concurrent-pages` = `120`

  Reduce these values if you hit rate limits:

  ```bash
  webtoon-downloader [url] --concurrent-chapters 2 --concurrent-pages 5
  ```

- **Proxy support**: if you're still rate limited, you can configure the downloader to use a proxy (e.g., local proxy pool or SOCKS proxy).

  ```bash
  webtoon-downloader [url] --proxy http://127.0.0.1:7890
  ```

If you continue to experience issues, experiment with different combinations of retry strategy and concurrency, or use a rotating proxy setup.

### Other Options

- Change image format (e.g., png, jpg):

  ```bash
  webtoon-downloader [url] --image-format png
  ```

- Set output folder:

By default, the downloaded chapters will be stored under the current working directory with the folder name \[series_title].

Example:

```
Tower_of_God
    ├── 150_001.jpg
    ├── 150_002.jpg
    ├── 150_003.jpg
    └── ...
```

Otherwise, use `--out` to specify a custom directory:

```bash
webtoon-downloader [url] --out ./my_folder
```

- Save chapters into **separate folders** corresponding to each chapter:

  ```bash
  webtoon-downloader [url] --separate
  ```

  For example, downloading Tower of God, Chapter 150 to 152 would result in:

  ```
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

- Export summary, chapter titles, and author notes:

  ```bash
  webtoon-downloader [url] --export-metadata --export-format json
  ```

- Change storage format (e.g., zip, cbz, pdf):

  ```bash
  webtoon-downloader [url] --save-as cbz
  ```

- Enable debug logging:

  ```bash
  webtoon-downloader [url] --debug
  ```

- Use a proxy server:

  ```bash
  webtoon-downloader [url] --proxy http://127.0.0.1:7890
  ```

- Set retry strategy for failed requests (exponential, linear, fixed, none):

  ```bash
  webtoon-downloader [url] --retry-strategy exponential
  ```

  n.b. `none` will disable retries, so use with caution.

- Control concurrency to avoid rate limits:

  ```bash
  webtoon-downloader [url] --concurrent-chapters 2 --concurrent-pages 5
  ```

---

## Contributing

Any contributions you make are **greatly appreciated**.

1. Fork the repo
2. Create a branch (`git checkout -b feature/new-idea`)
3. Commit changes (`git commit -m 'Add new idea'`)
4. Push to GitHub (`git push origin feature/new-idea`)
5. Create a pull request

---

## License

Distributed under the MIT License. See `LICENSE` for more.

---

## Contact

**Zehina** – [zehinadev@gmail.com](mailto:zehinadev@gmail.com)
[Project homepage](https://github.com/Zehina/Webtoon-Downloader)

---

## Built With

- [Rich](https://github.com/Textualize/rich) — Beautiful terminal formatting
- [Webtoons](https://www.webtoons.com/) — For the accessibility to thousands of free comics.
- Many other libraries and tools used in this project can be found in the [pyproject.toml](https://github.com/Zehina/Webtoon-Downloader/blob/master/pyproject.toml) file.

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[contributors-shield]: https://img.shields.io/github/contributors/Zehina/repo.svg?style=for-the-badge
[contributors-url]: https://github.com/Zehina/Webtoon-Downloader/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Zehina/repo.svg?style=for-the-badge
[forks-url]: https://github.com/Zehina/Webtoon-Downloader/network/members
[stars-shield]: https://img.shields.io/github/stars/Zehina/repo.svg?style=for-the-badge
[stars-url]: https://github.com/Zehina/Webtoon-Downloader/stargazers
[issues-shield]: https://img.shields.io/github/issues/Zehina/repo.svg?style=for-the-badge
[issues-url]: https://github.com/Zehina/Webtoon-Downloader/issues
[license-shield]: https://img.shields.io/github/license/Zehina/repo.svg?style=for-the-badge
[license-url]: https://github.com/Zehina/Webtoon-Downloader/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/Zehina
