from pathlib import Path

class MDFile:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.filename = path.name

class CombinedMDFile(MDFile):
    def __init__(self, path: Path, files: list[MDFile]):
        super().__init__(path)
        self.files = files