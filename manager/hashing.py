
import os
import hashlib
from pathlib import Path
from typing import Any

def hash_file(file: Path, buf_size: int = 16 * 1024) -> Any:
    hsh = hashlib.sha1()

    with open(file, 'rb') as fp:
        while True:
            buf = fp.read(buf_size)
            if not buf: break

            hsh.update(buf)

    return hsh

def hash_dir(directory: Path) -> Any:
    hsh = hashlib.sha1()

    if not directory.exists(): return hsh

    for root, _, files in os.walk(directory):
        for f in files:
            path = Path(root, f)

            hsh.update(hash_file(path).digest())
    
    return hsh
