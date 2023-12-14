from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='Webtoon_Downloader',
    version='0.7.0',
    description='Webtoons Scraper for downloading chapters of any series hosted on the webtoons website.',
    author='Ali Taibi',
    author_email='zehinadev@gmail.com',
    url='https://github.com/Zehina/Webtoon-Downloader',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License: OSI Approved :: MIT License'
    ],
    long_description=long_description,
    license='MIT',
    keywords='webtoon, downloader, scraper',
    packages=[
        'Webtoon_Downloader',
        'Webtoon_Downloader.data',
    ],
    package_dir={
        'Webtoon_Downloader': 'src',
        'Webtoon_Downloader.data': '',
    },
    package_data={
        'Webtoon_Downloader.data': ['README.md'],
    },
    python_requires='>=3.7, <4',
    install_requires=['requests>=2.26.0', 'beautifulsoup4>=4.10.0', 'rich>=10.10.0', 'Pillow>=8.3.1', 'lxml>=4.6.3'],
    entry_points={
        'console_scripts': [
            'webtoon-downloader = Webtoon_Downloader.webtoon_downloader:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/Zehina/Webtoon-Downloader/issues',
        'Source': 'https://github.com/Zehina/Webtoon-Downloader/',
    },
)
