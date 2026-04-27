import time
import random

import cloudscraper
import browser_cookie3

from .constants import Route
from .utility import _parse_project_names


class OverleafClient:
    def __init__(self, ) -> None:
        self._projects: dict[str, str] = {}
        self._selected_id = ""
        self._selected_name = ""

        self.cookies = browser_cookie3.firefox(domain_name=Route.HOST)
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "firefox", "platform": "linux", "mobile": False}
        )
        self.scraper.cookies.update(self.cookies)

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        }

    # ---------------------------------------------------------------- properties

    @property
    def selected_name(self) -> str:
        return self._selected_name

    @property
    def selected_id(self) -> str:
        return self._selected_id

    @selected_id.setter
    def selected_id(self, value: str) -> None:
        self._selected_name = self._projects[value]
        self._selected_id = value

    # ------------------------------------------------------------------- private

    def _get(self, url: str, stream: bool = False):
        response = self.scraper.get(url, headers=self.headers, stream=stream)
        return response

    # -------------------------------------------------------------------- public

    def fetch_all_projects(self) -> dict[str, str]:
        response = self._get(Route.MAIN + Route.PROJECT)
        self.raw_data = _parse_project_names(response)
        self._projects = {p["id"]: p["name"] for p in self.raw_data["projects"]}
        return self._projects

    def connect_project(self) -> str:
        if not self._selected_id:
            raise ValueError("No project selected — set selected_id first.")
        t = int(time.time() * 1000) + random.randint(0, 1000)
        url = Route.MAIN + Route.SOCKETIO + f"?projectId={self._selected_id}&t={t}"
        token = self._get(url).text.split(":")[0]
        return token

