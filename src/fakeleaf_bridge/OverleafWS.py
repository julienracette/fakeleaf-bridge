import asyncio
import json
import websockets

from .utility import print_other_terminal, parse_sharejs_ot,compute_doc_hash


class OverleafWS:
    def __init__(self, cookies, host,debug= False):
        self.cookies = cookies
        self.host = host
        self.ws = None
        self._joined = False
        self.verbose= True
        self._max_position =0 
        self._doc_lines = []
        self._debug = debug
        self._queue = asyncio.Queue()


    @property
    def debug(self):
        return self._debug


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
            self.ws = ws
            print_other_terminal("WebSocket connected!", debug=self.debug)

            # Step 1: wait for server's "1::" connect confirmation
            first = await ws.recv()
            print_other_terminal(f"← {first}", debug=self.debug)
            # first should be "1::" — just acknowledge it, do NOT send it back

            # Step 2: emit joinProject immediately
            await self._emit(ws, "joinProject", {"project_id": project_id})

            # Step 3: listen forever
            await asyncio.gather( 
                                 self._listen(ws, project_id),
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
        print_other_terminal(f"→ [{event_name}] {frame}", debug=self.debug)
        await ws.send(frame)

    async def _listen(self, ws, project_id: str):
        async for message in ws:
            await self._handle_frame(ws, message, project_id)

    async def _handle_frame(self, ws, frame: str, project_id: str):

        # Socket.IO v0.9 frame: type:id:endpoint:data
        parts = frame.split(":", 3)
        msg_type = parts[0]
        if self.verbose and parts[0] !="2":
            print_other_terminal("--------------------------------", debug=self.debug)
            print_other_terminal(f"Message type:{parts[0]}", debug=self.debug)
            print_other_terminal(parts[3], debug=self.debug)
            print_other_terminal("--------------------------------", debug=self.debug)

        match msg_type:
            case "2":
                # Heartbeat ping from server — must pong back
                await ws.send("2::")
                print_other_terminal("→ Pong", debug=self.debug)

            case "1":
                # Connect frame — server is confirming endpoint, do NOT reply
                print_other_terminal("   (endpoint connected, ignoring)", debug=self.debug)

            case "5":
                # Event
                try:
                    data = json.loads(parts[3])
                    name = data.get("name", "")
                    args = data.get("args", [])
                    await self._dispatch(ws, name, args, project_id)
                except json.JSONDecodeError as e:
                    print_other_terminal(f"JSON parse error: {e}", debug=self.debug)

            case "4":
                # Raw JSON message
                if len(parts) == 4:
                    print_other_terminal(f"📄 JSON msg: {parts[3]}", debug=self.debug)

            case "7":
                print_other_terminal(f"Server error: {frame}", debug=self.debug)

            case "6":
                print_other_terminal("Message 6:", debug=self.debug)
                try:
                    data = parse_sharejs_ot(parts[3])
                    if "lines" in data:
                        self._doc_lines= data["lines"]
                        for line in self._doc_lines:
                            self._max_position+=len(line)

                        self._doc_version = data["revision"]
                        print_other_terminal(f"📄 Doc joined | v={self._doc_version} | {len(self._doc_lines)} lines", debug=self.debug)
                        print_other_terminal(f"   Hash check: {compute_doc_hash(self._doc_lines)}", debug=self.debug)
                        print_other_terminal(f"New max position: {self._max_position}", debug=self.debug)
                except json.JSONDecodeError as e:
                    print_other_terminal(f"JSON parse error: {e}", debug=self.debug)

            case _:
                print_other_terminal(f"Unknown type {msg_type}", debug=self.debug)

    async def _dispatch(self, ws, event: str, args: list, project_id: str):
        events = event.split(".")
        match events[0]:
            case "joinProjectResponse":
                if self._joined:
                    print_other_terminal("Duplicate joinProjectResponse ignored", debug=self.debug)
                    return
                self._joined = True
                project = args[0].get("project", {})
                print_other_terminal(f"Joined: {project.get('name')}", debug=self.debug)

                # Now join the root document
                root_doc_id = project.get("rootDoc_id")
                if root_doc_id:
                    await self.join_doc(ws, root_doc_id)

            case "joinDocResponse":
                print_other_terminal(f"Doc content received: {args}", debug=self.debug)

            case "otUpdateApplied":
                print_other_terminal(f"OT update: {args}", debug=self.debug)
                self._doc_version+=1

            case "clientTracking":
                if events[1]== "clientUpdated":
                    print_other_terminal("Client updated!", debug=self.debug)

            case "broadcastDocMeta":
                print_other_terminal(f"Doc meta: {args}", debug=self.debug)

            case _:
                print_other_terminal(f"Not dispatched event:{event}", debug=self.debug)
                print_other_terminal(f"Args: {args}", debug=self.debug)
    
    async def join_doc(self, ws, doc_id: str):
        self._current_id = doc_id
        print_other_terminal(f"→ joinDoc sent for {doc_id}", debug=self.debug)

        await self._emit(ws, "clientTracking.getConnectedUsers", id="1")
        await self._emit(ws, "joinDoc", doc_id, {"encodeRanges": True, "supportsHistoryOT": True}, id="2+")


    async def _handle_bridge_event(self,ws,msg):
        if msg["event"] == "sendModification":
            await self._send_edit(ws,msg["args"][])
        



    def _apply_local_insert(self, text: str, position: int):
        full = "\n".join(self._doc_lines)
        full = full[:position] + text + full[position:]
        self._doc_lines = full.split("\n")
        self._max_position = len(full)
