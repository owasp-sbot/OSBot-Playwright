import os
from unittest                                               import TestCase
from fastapi                                                import FastAPI
from osbot_utils.utils.Env                                  import load_dotenv
#from osbot_fast_api.utils.http_shell.Http_Shell__Server     import ENV__HTTP_SHELL_AUTH_KEY
from osbot_utils.utils.Functions                            import function_source_code
from osbot_utils.utils.Misc                                 import  bytes_to_str
from starlette.responses                                    import HTMLResponse
from starlette.testclient                                   import TestClient

from osbot_playwright.playwright.fastapi.Routes__Playwright import Routes__Playwright, ROUTES_PATHS__PLAYWRIGHT, \
    ROUTES_METHODS__PLAYWRIGHT


class test_Routes__Playwright(TestCase):

    @classmethod
    def setUpClass(cls):
        import pytest
        pytest.skip("Fast API needs updating to latest Fast_API mode")  # todo: fix this

    def setUp(self):
        self.app               = FastAPI()
        self.client            = TestClient(self.app)
        self.routes_playwright = Routes__Playwright(app=self.app)


    def auth_key(self):
        load_dotenv()
        return os.environ.get(ENV__HTTP_SHELL_AUTH_KEY)

    def test_code(self):
        expected_result = { 'result': { 'title': 'Error 404 (Not Found)!!1',
                            'url'   : 'https://www.google.com/404'}        ,
                            'status': 'ok'                                 }
        def callback(browser):
            page = browser.new_page()
            page.goto('https://www.google.com/404')
            url = page.url
            title = page.title()
            return { 'url': url, 'title': title }

        method_code = function_source_code(callback)

        data = dict(auth_key=self.auth_key(),
                    code=method_code)

        response = self.client.post('/playwright/code', json=data)
        assert response.status_code == 200
        assert response.json() == expected_result

    def test_html(self):
        url      = 'https://httpbin.org/get'
        response = self.routes_playwright.html(url)
        assert type(response) is HTMLResponse
        assert response.status_code == 200
        assert response.media_type  == "text/html"
        assert '"url": "https://httpbin.org/get"' in bytes_to_str(response.body)


    def test_screenshot(self):
        #png_signature      = b'\x89PNG\r\n\x1A\n'
        url                = 'https://httpbin.org/get'
        streaming_response = self.routes_playwright.screenshot(url)

        assert streaming_response.charset       == "utf-8"
        assert streaming_response.media_type    == "image/png"
        assert streaming_response.status_code   == 200
        assert dict(streaming_response.headers) == {'content-type': 'image/png'}





    def test_routes_paths(self):
        assert self.routes_playwright.routes_methods() == ROUTES_METHODS__PLAYWRIGHT
