

import json
from pathlib import Path

from typing import (
    Any
)

class _Config:
    def __init__(self):
        self._loaded = False
        self._data = {}
        
        self.file = None

    def _load(self):
        if self.file is None:
            raise Exception('File has not been set')

        with open(self.file) as fp:
            self._data = json.load(fp)

        self._loaded = True

        return self

    def _get(self, *args):
        if not self._loaded:
            self._load()

        return self._data.get(*args)
    
    def __getattr__(self, *args) -> Any:
        return self._get(*args)

    def set_json_file(self, file: Path):
        self.file = file

config = _Config()
