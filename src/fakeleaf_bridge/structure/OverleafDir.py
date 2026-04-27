from .OverleafFile import OverleafFile
class OverleafDir:
    def __init__(self,d)-> None:
        self._id = d.get("id")
        self._name= d.get("name")
        self._files =[OverleafFile(file) for file in d.get("docs")] 
        self._subfolders = [OverleafDir(subfolder) for subfolder in d.get("folders") ]
    
    #------------------------------------------------- Getters
    @property
    def id(self):
        return self._id
    @property
    def name(self):
        return self._name
    @property
    def files(self):
        return self._files
    @property
    def subfolders(self):
        return self._subfolders
    def __str__(self, indent: int = 0) -> str:
        pad = "  " * indent
        lines = [f"{pad} {self._name}/"]
        for file in self._files:
            lines.append(f"{pad}  {file}")
        for sub in self._subfolders:
            lines.append(sub.__str__(indent + 1))
        return "\n".join(lines)


