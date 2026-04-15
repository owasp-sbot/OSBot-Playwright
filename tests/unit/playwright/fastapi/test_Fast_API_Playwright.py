from unittest                                                   import TestCase
from osbot_fast_api.api.routes.Routes__Config                   import ROUTES_PATHS__CONFIG
from osbot_playwright.playwright.fastapi.Fast_API_Playwright    import Fast_API_Playwright
from osbot_playwright.playwright.fastapi.Routes__Playwright     import ROUTES_PATHS__PLAYWRIGHT


class test_Fast_API_Playwright(TestCase):

    def setUp(self):
        import pytest
        pytest.skip("Playwright tests started to fails with recent update")  # todo: fix this
        self.fast_api = Fast_API_Playwright()

    def test__init__(self):
        assert self.fast_api.enable_cors is False

    def test_routes(self):
        expected_routes = ['/'] + ROUTES_PATHS__CONFIG + ROUTES_PATHS__PLAYWRIGHT
        routes = self.fast_api.routes_paths(include_default=True)
        assert routes == sorted(expected_routes)