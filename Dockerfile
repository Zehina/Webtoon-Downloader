ARG PYTHON_VERSION=3.11-buster
FROM python:${PYTHON_VERSION}
COPY pyproject.toml /
COPY src /src/
RUN pip install .
ENTRYPOINT ["python"]
CMD ["/src/webtoon_downloader.py"]
