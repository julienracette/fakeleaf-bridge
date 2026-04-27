class OverleafFile:
    def  __init__(self,d)->None:
        self._id = d.get("id")
        self._name= d.get("name")
        self.content=""

    #----------------------------------------------- Getters
    @property
    def id(self):
        return self._id
    @property
    def name(self):
        return self._name
    def __str__(self) -> str:
        return f"{self.name}:{self.id}"



