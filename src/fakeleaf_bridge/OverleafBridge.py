import sys
import json
import asyncio

from .OverleafClient import OverleafClient
from .OverleafWS import OverleafWS
from .constants import Route

class OverleafBridge:
    async def run(self):
        self._loop = asyncio.get_event_loop()
        self._client = OverleafClient()
        self._ows = OverleafWS(self._client.scraper.cookies, Route.HOST)
        await self._loop.run_in_executor(None, self.read_loop)


    def read_loop(self):
        for line in sys.stdin:
            if not line.strip():
                continue

            msg = json.loads(line)
            self.handle(msg)

    def send(self, msg):
        print(json.dumps(msg), flush=True)

    def handle(self, msg):
        t = msg.get("type")
        if t== "fetch":
            self.handle_fetch()
        elif t == "connect":
            self.handle_connect(msg)
        else:
            self.send({
                "type": "error",
                "message": f"Unknown type: {t}"
                })



    #Handlers
    def handle_fetch(self):
        projects_dict=self._client.fetch_all_projects()
        self.send({
            "type": "projects_dict",
            "content": json.dumps(projects_dict)
            })

    def handle_connect(self, msg):
        token = self._client.connect_project()
        asyncio.run_coroutine_threadsafe(self._ows.connect(token, self._client.selected_id),self._loop)


        
