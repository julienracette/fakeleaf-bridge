from enum import Enum

class Route(str,Enum):
    HOST = "overleaf.com"
    MAIN= "https://www.overleaf.com/"
    PROJECT ="project"
    PROJECT_DIR ="project/"
    SOCKETIO = "socket.io/1/"
    WEBSOCKET="websocket/"
    DOWNLOAD="download/zip"
    def __str__(self):
        return self.value

class Path(str,Enum):
    RESPONSE= "data/response/"
    TEMP="data/temp/"
    PROJECT = "data/projects/"

    def __str__(self):
        return self.value

