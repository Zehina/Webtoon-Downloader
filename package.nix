{
  python3,
  lib,
}:

let
  pyproject = fromTOML (builtins.readFile ./pyproject.toml);
in

python3.pkgs.buildPythonApplication {
  pname = "webtoon_downloader";
  inherit (pyproject.tool.poetry) version;

  pyproject = true;
  src = ./.;

  build-system = with python3.pkgs; [
    poetry-core
  ];

  dependencies = with python3.pkgs; [
    aiofiles
    beautifulsoup4
    furl
    httpx
    h2
    lxml
    pillow
    pymupdf
    rich
    rich-click
    typing-extensions
  ];

  pythonRelaxDeps = [
    "aiofiles"
    "httpx"
    "lxml"
    "pillow"
    "rich"
  ];

  pythonImportsCheck = [ "webtoon_downloader" ];

  nativeCheckInputs = with python3.pkgs; [
    pytestCheckHook
    pytest-asyncio
  ];

  disabledTestPaths = [
    "tests/test_extractors.py" # requires network
  ];

  meta = {
    description = "Webtoons Scraper able to download all chapters of any series wanted";
    homepage = "https://github.com/Zehina/Webtoon-Downloader";
    license = lib.licenses.mit;
    mainProgram = "webtoon-downloader";
  };
}
