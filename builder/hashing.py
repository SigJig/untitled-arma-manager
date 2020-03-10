
import os
import hashlib
from pathlib import Path

def hash_file(file: Path, buf_size=16 * 1024):
    hsh = hashlib.sha1()

    try:
        with open(file, 'rb') as fp:
            while True:
                buf = fp.read(buf_size)
                if not buf: break

                hsh.update(buf)
    except IOError:
        print(f'Unable to open file {file}')

    return hsh

def hash_dir(directory: Path):
    hsh = hashlib.sha1()

    if not directory.exists(): return hsh

    for root, _, files in os.walk(directory):
        for f in files:
            path = Path(root, f)

            hsh.update(hash_file(path).digest())
    
    return hsh
