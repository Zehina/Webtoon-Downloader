# FAQ

This page is based on recurring themes from the project issue tracker, including both open and closed issues.

## Why Do I Get Rate Limited, Read Timeouts, Or Incomplete Downloads?

This is one of the most common failure classes.

Typical causes:

- Webtoons rate limiting bursty traffic
- image CDN stalls or slow responses
- concurrency set too high for the current network or region

Things to try:

- lower `--concurrent-chapters`
- lower `--concurrent-pages`
- keep `--retry-strategy` enabled
- use `--proxy`
- retry later when the upstream site is calmer

This is not something the project can fully eliminate because the server decides when to throttle or stall requests.

## Can This Download Daily Pass Or App-Only Chapters?

No, not reliably.

The downloader targets the public Webtoons website flow. If chapters are only exposed through the official app or hidden behind Daily Pass logic, they are outside the normal source this project uses.

## Why Did A Series Suddenly Stop Working Even Though It Worked Before?

Webtoons changes site markup, viewer structure, and localized layouts over time.

When that happens:

- HTML selectors can break
- viewer metadata can move
- titles or image nodes can disappear from expected locations

That class of breakage requires a code update. If you hit it, open an issue with:

- the failing URL
- the exact command you ran
- the error output
- `--debug` logs if available

## Why Does The Displayed Chapter Number Not Match `episode_no` In The URL?

Webtoons sometimes exposes an `episode_no` in the URL that does not match the numbering displayed in the series UI.

The downloader currently follows the chapter numbering extracted from the site itself, not arbitrary external numbering from RSS feeds or URL parameters.

## Why Does `webtoon-downloader` Say `command not found`?

That is usually an installation or `PATH` problem.

Check the basics:

- install with `uv tool install webtoon_downloader` or `pipx install webtoon_downloader`
- reopen your terminal
- confirm the install location is on `PATH`
- run `webtoon-downloader --version`

## Why Does `pip` Say It Is Not Found?

That is also a local Python environment problem, not a downloader bug.

Prefer one of these flows instead of manual `pip` troubleshooting:

- `uv tool install webtoon_downloader`
- `pipx install webtoon_downloader`

## Why Am I Seeing “No Images Found” Or Missing Element Errors?

That usually means one of these:

- Webtoons changed the page markup
- the chapter viewer is behaving differently for that series
- the series is unavailable in the way the downloader expects

This is a real bug class, but it is usually upstream-driven rather than caused by user input.

## Can The Project Prevent Every Failure Automatically?

No.

The project can improve retry logic, parsing, and validation, but some failures remain outside its control:

- Webtoons rate limiting
- Daily Pass and app-only gating
- upstream HTML/API changes
- local Python, PATH, or proxy problems

## Should I Open An Issue Or Is It Just A Known Limitation?

Open an issue if:

- the URL is public and should work
- the command is valid
- the failure is reproducible
- you can provide logs or exact output

It is more likely a limitation if:

- the content is Daily Pass or app-only
- the failure is just temporary rate limiting
- the tool is not installed correctly on your machine
