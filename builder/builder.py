
import os
import shutil
from typing import (
    Type,
    Any
)
from pathlib import Path
from joiner import Joiner
from hashing import hash_dir

# Possibly a user-defined class that sets instructions on how to compile the source files?
# Option to pass custom packager (for example if you wanted to use a different PBO packer or ObfuSQF)
class Builder:
    def __init__(self, 
            source_dir: Path,
            out_dir: Path,
            missions_dir: Path,
            joiner: Type[Joiner]
        ) -> None:

        self.source_dir = source_dir
        self.out_dir = out_dir
        self.missions_dir = missions_dir
        self.joiner = joiner

    def _verify_dir(self, dir_: Path) -> None:
        if not dir_.exists():
            dir_.mkdir()

    def _merge(self, src: Path, dst: Path) -> None:
        self._verify_dir(dst)

        for entry in os.scandir(src):
            name = entry.name
            src_joined, dst_joined = (x.joinpath(name) for x in (src, dst))

            if not entry.is_file():
                name = entry.name

                self._merge(src_joined, dst_joined)
            else:
                shutil.copy(src_joined, dst_joined)

    def _join_sources(self) -> None:
        self._verify_dir(self.out_dir)

        joiner = self.joiner()

        for path in joiner.paths:

            # pylint: disable=unsubscriptable-object
            src = self.source_dir.joinpath(path[0])
            dst = self.out_dir.joinpath(path[1] if len(path) > 1 else src)

            if src.is_dir():
                if dst.exists():
                    if not dst.is_dir():
                        raise TypeError('Source is a directory, however destination is not.')

                    self._merge(src, dst)
                else:
                    shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)

    def build(self) -> Any:
        if self.out_dir.exists():
            shutil.rmtree(self.out_dir)
        
        self._join_sources()

        return hash_dir(self.out_dir)