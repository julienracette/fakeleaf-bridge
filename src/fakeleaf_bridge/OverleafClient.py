import cloudscraper
import browser_cookie3
from http import cookiejar
import json
from bs4 import BeautifulSoup
import pandas as pd
import os
from pprint import pprint
import time
from datetime import datetime
from requests import cookies
import socketio
import threading
import requests
import html
import time
import random
import asyncio
import zipfile


from .constants import Route, Path

class OverleafClient:
    def __init__(self,debug=False) -> None:
        for path in Path:
            if not os.path.isdir(path):
                os.makedirs(path)

        self._projects ={}
        self._selected_id = ""
        self._selected_name=""
        self._debug = debug
        self.cookies = browser_cookie3.firefox(domain_name=Route.HOST)
        self.scraper = cloudscraper.create_scraper(    
                                                   browser={
                                                       'browser': 'firefox',
                                                       'platform': 'linux',
                                                       'mobile': False

                                                       }

                                                   )
        if self._debug:
            os.environ['REQUESTS_CA_BUNDLE'] = '/home/julienr/Downloads/burp_bundle.pem'
            self.scraper.proxies = {
                    "http": "http://127.0.0.1:8080",
                    "https": "http://127.0.0.1:8080"
                    }
            self.scraper.verify= ""
        self.headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",

                }
        self.scraper.cookies.update(self.cookies)

    @property
    def selected_name(self):
        return self._selected_name

    @property
    def debug(self):
        return self._debug

    @property
    def selected_id(self):
        return self._selected_id

    @selected_id.setter
    def selected_id(self, value):
        try:
            self._selected_name = self._projects[value]
            self._selected_id = value
        except Exception as e:
            raise e


    def __get(self,url:str,stream=False):
        response = self.scraper.get(url,headers=self.headers,stream=stream)
        if self.debug:
            print(f"{url} fetched!")
            print(f"Status code: {response.status_code}")
        return response

    def fetch_all_projects(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        response = self.__get(Route.MAIN + Route.PROJECT)
        with open(f"{Path.RESPONSE}overleaf_fetch_project_{ts}.html","w+") as file:
            file.write(response.text)
        self.raw_data = self._parse_project_names(response)
        for p in self.raw_data["projects"]:
            self._projects[p["id"]] = p["name"]
        return self._projects


    def connect_project(self):
        if self.selected_id =="":
            raise Exception("No id selected")
        t = int(time.time() * 1000) + random.randint(0, 1000)
        url= Route.MAIN + Route.SOCKETIO +f"?projectId={self._selected_id}&t={t}"
        response = self.__get(url)

        parts = response.text.split(":")
        token = parts[0]
        if self.debug:
            print(f"Got token: {token}")
        return token


    def fetch_doc(self):
        resp = self.__get(Route.MAIN + Route.PROJECT_DIR+self._selected_id+"/"+ Route.DOWNLOAD, stream=True)
        resp.raise_for_status()
        path =f"{Path.PROJECT}{self._selected_name}/"
        with open(f"{Path.TEMP}{self._selected_name}.zip", "wb+") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        if not os.path.isdir(path):
            os.makedirs(path)
        with zipfile.ZipFile(f"{Path.TEMP}{self._selected_name}.zip",'r') as zip_ref:
            zip_ref.extractall(path)

    def _parse_project_names(self,response):
        soup = BeautifulSoup(response.text, "html.parser")
        meta = soup.find("meta", {"name": "ol-prefetchedProjectsBlob"})
        if meta is None:
            raise Exception("No content")
        data = json.loads(html.unescape(str(meta["content"])))
        return data







