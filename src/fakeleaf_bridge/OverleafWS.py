import sys
import asyncio
import json
import websockets

from .utility import parse_sharejs_ot, compute_doc_hash, parse_project,  get_doc_path


class OverleafWS:
    def __init__(self, cookies, host, on_message=None):
        self.cookies = cookies
        self.host = host
        self.ws = None
        self._joined = False
        self._max_position = 0
        self._doc_lines = []
        self._queue = asyncio.Queue()
        self._on_message = on_message or (lambda msg: None)
        self._request_count = 0
        self._first_file_opened = False
        self._open_doc_id = None

    # ------------------------------------------------------------------ helpers

    async def _debug(self, msg):
        await self._notify({"type": "debug", "message": msg})

    async def _notify(self, payload):
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._on_message, payload)
        except Exception as e:
            print(f"NOTIFY CRASH: {e}", file=sys.stderr, flush=True)
            raise

    # ----------------------------------------------------------------- connect

    async def connect(self, token: str, project_id: str):
        self._loop = asyncio.get_running_loop()
        self._current_id = project_id

        url = f"wss://www.{self.host}/socket.io/1/websocket/{token}?projectId={project_id}"
        cookie_str = "; ".join(f"{c.name}={c.value}" for c in self.cookies)
        headers = {
            "Cookie": cookie_str,
            "Origin": f"https://www.{self.host}",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
        }

        try:
            async with websockets.connect(url, additional_headers=headers, ping_interval=None, ping_timeout=None) as ws:
                await ws.recv()
                await self._emit(ws, "joinProject", {"project_id": project_id})
                await asyncio.gather(self._listen(ws), self._bridge_loop(ws))
        except Exception as e:
            print(f"CONNECT CRASH: {e}", file=sys.stderr, flush=True)
            raise

    # --------------------------------------------------------------- messaging

    def enqueue(self, msg):
        asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)

    async def _emit(self, ws, event_name: str, *args, id=False, endpoint=""):
        payload = json.dumps({"name": event_name, "args": list(args)}, separators=(",", ":"))
        if id:
            self._request_count += 1
            frame = f"5:{self._request_count}+:{endpoint}:{payload}"
        else:
            frame = f"5::{endpoint}:{payload}"
        await self._debug(f"Sended:{frame}")
        await ws.send(frame)

    # ------------------------------------------------------------------- loops

    async def _listen(self, ws):
        async for message in ws:
            try:
                await self._handle_frame(ws, message)
            except Exception as e:
                print(f"LISTEN CRASH: {e}", file=sys.stderr, flush=True)
                raise

    async def _bridge_loop(self, ws):
        while not self._joined:
            await asyncio.sleep(0.1)

        while True:
            try:
                msg = await self._queue.get()
                await self._handle_bridge_event(ws, msg)
            except Exception as e:
                print(f"BRIDGE CRASH: {e}", file=sys.stderr, flush=True)
                raise

    # ----------------------------------------------------------- frame handler

    async def _handle_frame(self, ws, frame: str):
        await self._debug(f"Received:{frame}")
        parts = frame.split(":", 3)
        msg_type = parts[0]
        match msg_type:
            case "2":
                await ws.send("2::")

            case "5":
                try:
                    data = json.loads(parts[3])
                    await self._dispatch(ws, data.get("name", ""), data.get("args", []))
                except json.JSONDecodeError as e:
                    print(f"FRAME 5 JSON CRASH: {e}", file=sys.stderr, flush=True)
                    raise
            case "6":
                try:
                    data = parse_sharejs_ot(parts[3])
                    if "lines" in data:
                        self._doc_lines = data["lines"]
                        self._max_position = sum(len(line) for line in self._doc_lines)
                        self._doc_version = data["revision"]
                    await self._notify({
                        "type": "sendfile",
                        "lines": self._doc_lines,
                        "path": get_doc_path(self._project_structure, self._root_doc_id),
                    })
                except IndexError as e:
                    print(f"FRAME 6 CRASH: {e}", file=sys.stderr, flush=True)
                    raise            
                except Exception as e:
                    print(f"FRAME 6 CRASH: {e}", file=sys.stderr, flush=True)
                    raise            

            case _:
                await self._debug(f"Non-treated frame: {msg_type}")

    # --------------------------------------------------------- event dispatch

    async def _dispatch(self, ws, event: str, args: list):
        try:
            match event.split(".")[0]:
                case "joinProjectResponse":
                    if self._joined:
                        return
                    self._joined = True
                    project = args[0].get("project", {})
                    self._root_doc_id = project.get("rootDoc_id")
                    self._project_structure = parse_project(args)
                    await self._debug(f"{self._project_structure}")
                    await self._notify({"type": "doc_ids", "list": self._project_structure})
                    if self._root_doc_id:
                        await self.join_doc(ws, self._root_doc_id)

                case "otUpdateApplied":
                    self._doc_version += 1

                case _:
                    await self._debug(f"Event not supported: {event}")
        except Exception as e:
            print(f"DISPATCH CRASH on '{event}': {e}", file=sys.stderr, flush=True)
            raise

    # ------------------------------------------------------------ doc helpers

    async def join_doc(self, ws, doc_id: str):
        self._open_doc_id = doc_id
        if not self._first_file_opened:
            await self._emit(ws, "clientTracking.getConnectedUsers", id=True)
        await self._emit(ws, "joinDoc", doc_id, {"encodeRanges": True, "supportsHistoryOT": True}, id=True)
        self._first_file_opened = True

    async def leave_doc(self, ws, doc_id: str):
        await self._emit(ws, "leaveDoc", doc_id, id=True)

    # ---------------------------------------------------- bridge event handler

    async def _handle_bridge_event(self, ws, msg):
        if msg.get("type") == "sendModification":
            content = msg["args"]
            await self._receive_edit(ws, content["changes"], content["position"])

    async def _receive_edit(self, ws, changes: str, position: int):
        self._apply_local_insert(changes, position)
        op = {
            "doc": self._current_id,
            "op": [{"p": position, "i": changes}],
            "v": self._doc_version,
            "hash": compute_doc_hash(self._doc_lines),
        }
        await self._emit(ws, "applyOtUpdate", self._current_id, op, id=True)
        self._doc_version += 1

    def _apply_local_insert(self, text: str, position: int):
        full = "\n".join(self._doc_lines)
        full = full[:position] + text + full[position:]
        self._doc_lines = full.split("\n")
        self._max_position = len(full)
