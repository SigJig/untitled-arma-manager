
import shutil
from typing import Type
from pathlib import Path
from joiner import Joiner, AYUJoiner

# Possibly a user-defined class that sets instructions on how to compile the source files?
# Option to pass custom packager (for example if you wanted to use a different PBO packer or ObfuSQF)
class Builder:
    def __init__(self, 
            source_dir: Path, out_dir: Path, missions_dir: Path, joiner: Type[Joiner] = AYUJoiner
        ) -> None:

        self.source_dir = source_dir
        self.out_dir = out_dir
        self.missions_dir = missions_dir
        self.joiner = joiner

    def _verify_dir(self, dir_: Path) -> None:
        if not dir_.exists():
            dir_.mkdir()

    def _merge(self, src: Path, dst: Path) -> None:
        pass

    def _join_sources(self):
        self._verify_dir(self.out_dir)

        joiner = self.joiner()

        for path in joiner.paths:
            src = self.source_dir.joinpath(path[0])
            dst = self.out_dir.joinpath(path[1] if len(path) > 1 else src)

            if src.is_dir():
                if dst.exists():
                    if not dst.is_dir():
                        raise TypeError('hi!')

                    self._merge(src, dst)
                else:
                    shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)

    def build(self):
        pass
