#from osbot_fast_api.utils.http_shell.Http_Shell__Server import Http_Shell__Server
#from osbot_utils.utils.Dev import pprint
from osbot_fast_api.api.routes.Fast_API__Routes import Fast_API__Routes
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse, JSONResponse

#from osbot_fast_api.api.Fast_API_Routes import Fast_API_Routes

ROUTES_METHODS__PLAYWRIGHT = ['code'            ,'html'            , 'screenshot'                             ]
ROUTES_PATHS__PLAYWRIGHT   = ['/playwright/code','/playwright/html', '/playwright/screenshot', '/shell-server']

class CodeData(BaseModel):
    auth_key: str
    code    : str


class Auth_Exception(Exception):                    # refactor to Http_Shell__Server
    def __init__(self, name: str, message: str):
        self.name = name
        self.message = message

class Routes__Playwright(Fast_API__Routes):
    tag : str =  'playwright'

    def add_error_handler(self):
        @self.app.exception_handler(Auth_Exception)
        def custom_exception_handler(request: Request, exc: Auth_Exception):
            return JSONResponse( status_code=403,
                                 content={"status": "error", "error": f"{exc.name}: {exc.message}"})

    # def extract_callback_method(self, code_data):
    #     shell_server = Http_Shell__Server()
    #     auth_status = shell_server.check_auth_key(code_data.auth_key)
    #     if auth_status.get('auth_status') != 'ok':                      # to refactor this exception to the Http_Shell__Server
    #         raise Auth_Exception("Auth error", auth_status)
    #
    #     callback_code = code_data.code
    #     local_vars    = {}
    #     exec(callback_code, {}, local_vars)
    #     return  local_vars.get('callback')


    # def code(self, code_data: CodeData):
    #     try:
    #         callback = self.extract_callback_method(code_data)
    #         with sync_playwright() as p:
    #             browser = p.chromium.launch(args=["--disable-gpu", "--single-process"])
    #             result  = callback(browser)
    #         return {'status':'ok', 'result' : result }
    #     except Exception as error:
    #         return {'status':'error', 'error': f'{error}'}

    def html(self, url):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--disable-gpu", "--single-process"])
                page    = browser.new_page()
                page.goto(url)
                html_content = page.content()
                return HTMLResponse(content=html_content, status_code=200)
        except Exception as error:
            return f'{error}'

    def screenshot(self, url):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--disable-gpu", "--single-process"])
                page = browser.new_page()
                page.goto(url)
                screenshot_bytes = page.screenshot(full_page=True)
                return StreamingResponse(content=iter([screenshot_bytes]), media_type="image/png")
        except Exception as error:
            return f'{error}'

    def setup_routes(self, router=None):
        self.add_error_handler()
        #self.add_route_post(self.code     )
        self.add_route_get(self.html      )
        self.add_route_get(self.screenshot)

