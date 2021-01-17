

import os, re, json
from pathlib import Path

from dotenv import load_dotenv

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
        
        if env := getattr(self, 'env', None):
            if f := env.get('file', None):
                load_dotenv(dotenv_path=f)
            if vars_ := env.get('vars', {}):
                for k, v in vars_.items():
                    os.environ[k] = v

        return self

    def _get(self, *args):
        if not self._loaded:
            self._load()

        val = self._data.get(*args)

        a = self._handle_value(val)
        return a

    def _handle_string(self, value: str) -> str:
        def repl(match: re.Match) -> str:
            name = match.group(1)

            try:
                return str(os.environ[name])
            except KeyError:
                raise KeyError(f'Environment variable {name} not set')

        return re.sub(r'\$(?<!\\)\{(?<!\\)([a-zA-Z0-9_]*)\}(?<!\\)', repl, value)

    def _handle_value(self, value: Any):
        if isinstance(value, str):
            return self._handle_string(value)
        elif isinstance(value, dict):
            return {k: self._handle_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._handle_value(x) for x in value]
        else:
            return value
    
    def __getattr__(self, *args) -> Any:
        return self._get(*args)

    def set_json_file(self, file: Path):
        self.file = file

        self._load()

config = _Config()
