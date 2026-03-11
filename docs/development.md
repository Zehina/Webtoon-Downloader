# Development

This page is for contributors working on the repository locally.

## Local Setup

Clone the repo and sync dependencies with `uv`:

```bash
uv sync
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

The repository also provides:

```bash
make install
```

## Useful Commands

### Run The CLI

```bash
uv run webtoon-downloader --help
```

### Run The Main Checks

```bash
make check
```

That currently covers:

- `uv lock --check`
- pre-commit
- `mypy`
- `deptry`

### Run Tests

```bash
make test
```

or directly:

```bash
uv run pytest --cov --cov-config=pyproject.toml --cov-report=xml
```

### Build Documentation

```bash
make docs-test
```

or serve locally:

```bash
make docs
```

### Build Distributions

```bash
make build
```

## Repository Layout

| Path                              | Purpose                                                   |
| --------------------------------- | --------------------------------------------------------- |
| `webtoon_downloader/cmd`          | CLI entrypoints, user-facing exceptions, progress display |
| `webtoon_downloader/core`         | downloader logic, fetchers, models, exceptions            |
| `webtoon_downloader/storage`      | output writers                                            |
| `webtoon_downloader/transformers` | image transformation helpers                              |
| `tests/`                          | test suite                                                |
| `docs/`                           | MkDocs documentation                                      |

## Code Style Notes

Project tooling currently includes:

- `ruff`
- `mypy`
- `pytest`
- `pre-commit`

When editing code:

- keep async boundaries explicit
- prefer focused exceptions over broad user-facing messages
- keep CLI parsing separate from core downloader logic

## Where To Make Changes

### CLI Behavior

Start in:

- `webtoon_downloader/cmd/cli.py`
- `webtoon_downloader/cmd/exceptions.py`
- `webtoon_downloader/cmd/progress.py`

### Webtoon Parsing Or Fetching

Start in:

- `webtoon_downloader/core/webtoon/fetchers.py`
- `webtoon_downloader/core/webtoon/extractor.py`
- `webtoon_downloader/core/webtoon/api.py`

### Download Pipeline

Start in:

- `webtoon_downloader/core/webtoon/downloaders/comic.py`
- `webtoon_downloader/core/webtoon/downloaders/chapter.py`
- `webtoon_downloader/core/downloaders/image.py`

### Output Formats

Start in:

- `webtoon_downloader/storage/file.py`
- `webtoon_downloader/storage/zip.py`
- `webtoon_downloader/storage/pdf.py`

## Common Contributor Tasks

### Add A New CLI Flag

1. Add the option in `cmd/cli.py`
2. Thread it into `WebtoonDownloadOptions`
3. Apply it in the appropriate core component
4. Add tests
5. Update the docs

### Fix A Scraping Regression

1. Reproduce with a failing URL
2. Inspect the relevant HTML or API response
3. Update the fetcher or extractor
4. Add or update regression coverage
5. Document any new limitation if the site behavior changed

### Add A New Output Format

1. Implement an `AioWriter`
2. Wire it in from `comic.py`
3. Update the CLI docs and README
4. Add end-to-end tests where practical

## Release And Packaging

The project uses `uv_build` as its build backend and defines the CLI script in `pyproject.toml`:

```toml
[project.scripts]
webtoon-downloader = "webtoon_downloader.cmd.cli:run"
```

For publishing, see the repository make targets:

- `make build`
- `make publish`
- `make build-and-publish`
