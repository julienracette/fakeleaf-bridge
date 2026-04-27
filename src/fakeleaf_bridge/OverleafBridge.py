import sys
import json
import asyncio

from fakeleaf_bridge.structure.OverleafFile import OverleafFile
from fakeleaf_bridge.structure.OverleafDir import OverleafDir

from .OverleafClient import OverleafClient
from .OverleafWS import OverleafWS
from .constants import Route


class OverleafBridge:
    # -------------------------------------------------------------------- setup
    async def run(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._client = OverleafClient()
        self._ows = OverleafWS(
            self._client.scraper.cookies,
            Route.HOST,
            on_message=self._handle_server,
        )
        await self._loop.run_in_executor(None, self._read_loop)

    # ------------------------------------------------------------ I/O primitives

    def _send(self, msg: dict) -> None:
        print(json.dumps(msg), flush=True)

    def _read_loop(self) -> None:
        for line in sys.stdin:
            if line.strip():
                self.handle_ide(json.loads(line))

    # ----------------------------------------------------------- server → IDE

    def _handle_server(self, msg: dict) -> None:
        t = msg.get("type")
        match t:
            case "debug":
                self._send({"type": "debug", "message": msg.get("message")})
            case "doc_ids":
                self._root_folder = OverleafDir(msg.get("list"))
                print(self._root_folder)
                self._send({"type": "doc_ids", "list": msg.get("list")})
            case "sendfile":
                self._send({"type": "debug", "message":f"Path:{msg.get("path")}" })
                self._send({"type": "debug", "message":f"Path:{msg.get("lines")}" })
                self._send({
                    "type": "sendfile",
                    "lines": msg.get("lines"),
                    "path": msg.get("path"),
                })

    # ----------------------------------------------------------- IDE → server

    def handle_ide(self, msg: dict) -> None:
        t = msg.get("type")
        match t:
            case "fetch":
                self._handle_fetch()
            case "connect":
                self._handle_connect(msg)
            case _:
                self._send({"type": "error", "message": f"Unknown type: {t}"})

    def _handle_fetch(self) -> None:
        projects = self._client.fetch_all_projects()
        self._send({"type": "projects_dict", "content": json.dumps(projects)})

    def _handle_connect(self, msg: dict) -> None:
        project_id = msg.get("id")
        if not project_id:
            self._send({"type": "error", "message": "Missing project id in connect message."})
            return
        self._client.selected_id = project_id
        token = self._client.connect_project()
        asyncio.run_coroutine_threadsafe(
            self._ows.connect(token, self._client.selected_id),
            self._loop,
        )
