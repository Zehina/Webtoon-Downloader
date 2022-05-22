import requests

class WebtoonSession(requests.Session):
    def __init__(self):
        super().__init__()
        self._setup_headers(self._setup_user_agent())
        self._setup_cookies()
    
    def _setup_headers(self, user_agent: str) -> None:
        self.headers = {
            'dnt': '1',
            'user-agent': user_agent,
            'accept-language': 'en-US,en;q=0.9',
        }
        self.image_headers = {
            'referer': 'https://www.webtoons.com/',
            **self.headers
        }

    def _setup_cookies(self):
        self.cookies.set("needGDPR", "FALSE", domain=".webtoons.com")
        self.cookies.set("needCCPA", "FALSE", domain=".webtoons.com")
        self.cookies.set("needCOPPA", "FALSE", domain=".webtoons.com")
    
    def _setup_user_agent(self) -> str:
        import os
        if os.name == 'nt':
            user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                               'AppleWebKit/537.36 (KHTML, like Gecko)' 
                               'Chrome/92.0.4515.107 Safari/537.36')
        else:
            user_agent = ('Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)' 
                               'Gecko/20100101 Firefox/75.0')
        return user_agent