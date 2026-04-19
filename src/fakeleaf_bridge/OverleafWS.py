import asyncio
import json
import websockets

from .utility import parse_sharejs_ot,compute_doc_hash


class OverleafWS:
    def __init__(self, cookies, host,on_message=None):
        self.cookies = cookies
        self.host = host
        self.ws = None
        self._joined = False
        self.verbose= True
        self._max_position =0 
        self._doc_lines = []
        self._queue = asyncio.Queue()
        self._on_message = on_message or (lambda msg: None)
        self.debug("test")

    def debug(self,msg):
        self._on_message({
            "type":"debug",
            "message":msg,
            })
    async def connect(self, token: str, project_id: str):
        self._current_id = project_id
        url = f"wss://www.{self.host}/socket.io/1/websocket/{token}?projectId={project_id}"
        cookie_str = "; ".join([f"{c.name}={c.value}" for c in self.cookies])
        headers = {
                "Cookie": cookie_str,
                "Origin": f"https://www.{self.host}",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
                    ),
                }
        async with websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=None,               
                ping_timeout=None,
                ) as ws:
            await ws.recv()
            await self._emit(ws, "joinProject", {"project_id": project_id})
            await asyncio.gather( 
                                 self._listen(ws),
                                 self._bridge_loop(ws)
                                 )


    async def _bridge_loop(self, ws):
        while not self._joined:

            await asyncio.sleep(0.1)

        while True:
            msg = await self._queue.get()
            await self._handle_bridge_event(ws,msg)
            
    def enqueue(self, event, *args):
        asyncio.run_coroutine_threadsafe(
            self._queue.put({"event": event, "args": args}),
            asyncio.get_event_loop()
        )

    async def _send_edit(self, ws, changes: str, position: int):
        self._apply_local_insert(changes, position)
        op = {
                "doc": self._current_id,
                "op": [{"p": position, "i": changes}],  # position first, no lastV
                "v": self._doc_version,
                "hash": compute_doc_hash(self._doc_lines),
                }
        await self._emit(ws, "applyOtUpdate", self._current_id, op, id="3+")
        self._doc_version+=1

    async def _emit(self, ws, event_name: str, *args, id="", endpoint=""):
        payload = json.dumps({"name": event_name, "args": list(args)})
        frame = f"5:{id}:{endpoint}:{payload}"
        await ws.send(frame)

    async def _listen(self, ws):
        async for message in ws:
            await self._handle_frame(ws, message)

    async def _handle_frame(self, ws, frame: str ):
        parts = frame.split(":", 3)
        msg_type = parts[0]
        self.debug(f"message type:{msg_type}")
        self.debug(f"{json.dumps(parts)}")
        match msg_type:
            case "2":
                self.debug("case 2")
                await ws.send("2::")

            case "1":
                self.debug("case 1")
                pass

            case "5":
                # Event
                try:
                    data = json.loads(parts[3])
                    name = data.get("name", "")
                    args = data.get("args", [])
                    await self._dispatch(ws, name, args)
                except json.JSONDecodeError as e:
                    raise Exception(e)

            case "4":
                self.debug("case 4")
                pass

            case "7":
                raise Exception(frame)

            case "6":
                try:
                    data = parse_sharejs_ot(parts[3])
                    if "lines" in data:
                        self.debug("received lines")
                        self._doc_lines= data["lines"]
                        for line in self._doc_lines:
                            self._max_position+=len(line)

                        self._doc_version = data["revision"]
                        self._on_message(
                            {"type":"sendfile",
                             "lines":self._doc_lines
                             }
                            )
                except json.JSONDecodeError as e:
                    raise Exception(e)

            case _:
                pass

    async def _dispatch(self, ws, event: str, args: list):
        events = event.split(".")
        match events[0]:
            case "joinProjectResponse":
                if self._joined:
                    return
                self._joined = True
                project = args[0].get("project", {})
                self._root_doc_id = project.get("rootDoc_id")
                root_folder = project["rootFolder"][0]
                self._docs = {doc["_id"]: doc["name"] for doc in root_folder["docs"]}
                self._on_message({
                    "type": "doc_ids",
                    "list":self._docs
                         })
                self.debug(json.dumps(self._docs))
                if self._root_doc_id:
                    await self.join_doc(ws, self._root_doc_id)

            case "joinDocResponse":
                pass

            case "otUpdateApplied":
                self._doc_version+=1

            case "clientTracking":
                if events[1]== "clientUpdated":
                    pass

            case "broadcastDocMeta":
                pass

            case _:
                pass
    
    async def join_doc(self, ws, doc_id: str):
        self._current_id = doc_id
        await self._emit(ws, "clientTracking.getConnectedUsers", id="1")
        await self._emit(ws, "joinDoc", doc_id, {"encodeRanges": True, "supportsHistoryOT": True}, id="2+")

    async def _handle_bridge_event(self,ws,msg):
        if msg["event"] == "sendModification":
            content = msg["args"]
            await self._send_edit(ws,content["changes"],content["position"])

    def _apply_local_insert(self, text: str, position: int):
        full = "\n".join(self._doc_lines)
        full = full[:position] + text + full[position:]
        self._doc_lines = full.split("\n")
        self._max_position = len(full)
