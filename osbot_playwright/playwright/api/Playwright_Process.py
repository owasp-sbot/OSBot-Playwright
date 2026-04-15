import subprocess
from urllib.parse import urljoin

import psutil
from osbot_utils.utils.Env import get_env

from osbot_utils.utils.Files import path_combine, temp_folder_current, folder_create, folder_exists, file_exists, \
    file_delete, folder_delete_recursively
from osbot_utils.utils.Http import wait_for_port, port_is_open, wait_for_port_closed, GET, GET_json
from osbot_utils.utils.Json          import json_save_file, json_load_file
from osbot_utils.utils.Misc import date_now, date_time_now
from osbot_utils.utils.Process import stop_process
from osbot_utils.utils.Python_Logger import Python_Logger

# todo: refactor this class to remove all references to chromium (i.e. make it generic for all browsers)
DEFAULT_VALUE_DEBUG_PORT       = 9910
FORMAT_CHROME_DATA_FOLDER      = 'playwright_chrome_data_folder_in_port__{port}'
TARGET_HOST                    = 'localhost'
FILE_PLAYWRIGHT_PROCESS        = 'playwright_process.json'
CHROMIUM_PROCESS_NAME          = 'Chromium'
CHROMIUM_PARAM_DEBUG_PORT      = "--remote-debugging-port"
CHROMIUM_PARAM_DATA_FOLDER     = "--user-data-dir"
CHROMIUM_PARAM_HEADLESS        = "--headless"
CHROMIUM_USE_MOCK_KEYCHAIN     = "--use-mock-keychain"          # to prevent the blocking permissions dialog about: "Chrome wants to use your confidential information stored .."
ENV_VAR__PLAYWRIGHT__PROXY_URL = 'PLAYWRIGHT__PROXY_URL'

# for more chrome launched options see https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md

class Playwright_Process:

    def __init__(self, browser_path=None, headless=True, reuse_browser=True, debug_port=None):
        self.logger        = Python_Logger().setup()
        self.debug_port    = debug_port or DEFAULT_VALUE_DEBUG_PORT
        self.browser_path  = browser_path
        self.headless      = headless
        self.reuse_browser = reuse_browser
        self.proxy         = get_env(ENV_VAR__PLAYWRIGHT__PROXY_URL)
        #self._browser      = None


    def __enter__(self): return self
    def __exit__ (self, exc_type, exc_val, exc_tb): pass

    def config(self):
        return dict(debug_port                   = self.debug_port        ,
                    path_data_folder             = self.path_data_folder(),
                    path_file_playwright_process = self.path_file_playwright_process())

    def delete_process_details(self):
        return file_delete(self.path_file_playwright_process())

    def delete_browser_data_folder(self):
        browser_data_folder = self.path_data_folder()
        assert temp_folder_current() in browser_data_folder         # always double check that we are going to delete recursively in the right location
        folder_delete_recursively(browser_data_folder)
        return folder_exists(browser_data_folder)


    def GET(self, path=''):
        url = urljoin(self.url_browser_debug_page(), path)
        return GET(url)

    def GET_json(self, path=''):
        url = urljoin(self.url_browser_debug_page(), path)
        return GET_json(url)

    def healthcheck(self):
        config                         = self.config()
        data_folder_exists             = folder_exists(config.get('path_data_folder'))
        playwright_process_file_exists = file_exists(config.get('path_file_playwright_process'))
        process_details                = self.process_details()

        if process_details == {}:
            chromium_debug_port     = None                                          # todo refactor to remove chromium references and dependencies (i.e. run also firefox and webkit)
            chromium_process_id     = None
            chromium_process_exists = False
            chromium_process_status = None
        else:
            chromium_debug_port     = process_details.get('debug_port')
            chromium_process_id     = process_details.get('process_id')
            chromium_process_exists = True
            chromium_process_status = process_details.get('status'    )

        chromium_debug_port_match   = chromium_debug_port == self.debug_port
        if chromium_debug_port and chromium_debug_port_match:
            chromium_debug_port_open = port_is_open(chromium_debug_port)
        else:
            chromium_debug_port_open = False

        if (chromium_process_status =='running' or chromium_process_status=='sleeping') \
                and chromium_debug_port_match                                           \
                and chromium_debug_port_open                                            \
                and chromium_process_exists                                             \
                and data_folder_exists:
            healthy = True
        else:
            healthy = False
        return dict(chromium_debug_port            = chromium_debug_port            ,
                    chromium_debug_port_match      = chromium_debug_port_match      ,
                    chromium_debug_port_open       = chromium_debug_port_open       ,
                    chromium_process_id            = chromium_process_id            ,
                    chromium_process_exists        = chromium_process_exists        ,
                    chromium_process_status        = chromium_process_status        ,
                    data_folder_exists             = data_folder_exists             ,
                    healthy                        = healthy                        ,
                    playwright_process_file_exists = playwright_process_file_exists )

    def healthy(self):
        return self.healthcheck().get('healthy')

    def load_process_details(self):
        return json_load_file(self.path_file_playwright_process())

    def path_data_folder(self):
        data_folder_name = FORMAT_CHROME_DATA_FOLDER.format(port=self.debug_port)
        path_data_folder = path_combine(temp_folder_current(), data_folder_name)
        return path_data_folder

    def path_file_playwright_process(self):
        return path_combine(self.path_data_folder(), FILE_PLAYWRIGHT_PROCESS)

    def process_details(self):
        process_details = self.load_process_details()
        process_id            = process_details.get('process_id')
        if process_id:
            try:
                process = psutil.Process(process_id)
                process_details['status'] = process.status()                # add the status to the data loaded from disk
                process_details['url'   ] = self.url_browser_debug_page()   # add the url to the data loaded from disk
                return process_details
            except psutil.NoSuchProcess:
                pass
        return {}

    def process_id(self):
        return self.process_details().get('process_id')

    def process_status(self):
        return self.process_details().get('status')

    def process_running(self):
        return self.process_id() is not None

    def start_process(self):
        if self.process_running():
            self.logger.error("There is already an chromium process running")
            return False

        if self.debug_port is None:
            raise Exception("[Playwright_Process] in start_process the debug_port value was not set")

        if self.browser_path is None:
            raise Exception("[Playwright_Process] in start_process the browser_path value was not set")

        browser_data_folder = self.path_data_folder()
        params = [ self.browser_path                                    ,
                  f'{CHROMIUM_PARAM_DEBUG_PORT}={self.debug_port}'      ,
                  f'{CHROMIUM_PARAM_DATA_FOLDER}={browser_data_folder}' ,
                   CHROMIUM_USE_MOCK_KEYCHAIN                           ,
                   '--disable-infobars' ]

        if self.proxy:
            params.append(f'--proxy-server={self.proxy}')
            params.append('--ignore-certificate-errors')

        if self.headless:
            params.append(CHROMIUM_PARAM_HEADLESS)

        folder_create(browser_data_folder)                          # make sure folder exists (which in some cases is not created in time to save the process_details)

        process = subprocess.Popen(params)
        self.save_process_details(process, self.debug_port)

        if self.wait_for_debug_port() is False: #port_is_open(self.chrome_port) is False:
            raise Exception(f"in browser_start_process, port {self.debug_port} was not open after process start")

        self.logger.info(f"started process id {process.pid} with debug port {self.debug_port}")

        return True

    def stop_process(self):
        if self.process_running():
            process_id = self.process_id()
            if process_id:
                self.logger.info(f"Stopping Chromium process {process_id}")
                #self.close_all_context_and_pages()  # todo: check if this is needed
                stop_process(process_id)

                if wait_for_port_closed(TARGET_HOST, self.debug_port):
                    self.logger.info(f"Port {self.debug_port} is now closed")
                self.delete_process_details()
                self.logger.info(f"Chromium process {process_id} stopped and port {self.debug_port} is closed")
                return True
        return False

    def save_process_details(self, process, debug_port):
        data = {
                 'created_at'   : date_time_now()        ,
                 'debug_port'   : debug_port        ,
                 'headless'     : self.headless     ,
                 'process_args' : process.args      ,
                 'process_id'   : process.pid       ,
                'reuse_browser' : self.reuse_browser
                }
        json_save_file(data, self.path_file_playwright_process())
        return self

    def restart_process(self):
        self.stop_process()
        return self.start_process()

    def url_browser_debug_page(self, path=""):
        return f"http://{TARGET_HOST}:{self.debug_port}/{path}"

    def url_browser_debug_page_json(self, path="json"):
        return self.url_browser_debug_page(path)

    def url_browser_debug_page_json_version(self, path="json/version"):
        return self.url_browser_debug_page(path)

    def version(self):
        return self.GET_json('/json/version')

    def wait_for_debug_port(self):
        return wait_for_port(TARGET_HOST, self.debug_port, max_attempts=50)
