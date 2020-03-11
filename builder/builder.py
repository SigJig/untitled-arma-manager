
import os
import shutil
import abc
from typing import (
    Type,
    Any
)
from pathlib import Path
from pboutil import PBOFile
from joiner import Joiner
from hashing import hash_dir, hash_file

class Binarizer(abc.ABC):
    def __init__(self, path: Path, out_path: Path) -> None:
        self.path = path
        
        if not out_path.is_file():
            self.out_path = out_path.joinpath(path.name + '.pbo')
        else:
            self.out_path = out_path

        parent = self.out_path.parents[0]
        if not parent.exists():
            os.makedirs(parent)

    @abc.abstractmethod
    def binarize(self) -> Any:
        pass

class PBOPacker(Binarizer):
    def binarize(self) -> Path:
        file = PBOFile.from_directory(self.path)

        file.to_file(self.out_path)

        return self.out_path

# Possibly a user-defined class that sets instructions on how to compile the source files?
# Option to pass custom packager (for example if you wanted to use a different PBO packer or ObfuSQF)
class Builder:
    def __init__(self, 
            source_dir: Path,
            out_dir: Path,
            missions_dir: Path,
            joiner: Type[Joiner],
            binarizer: Type[Binarizer] = None,
            should_binarize: bool = False
        ) -> None:

        self.source_dir = source_dir
        self.out_dir = out_dir
        self._out_file = None
        self.missions_dir = missions_dir
        self.joiner = joiner

        if binarizer is None and should_binarize:
            raise Exception('Binarize option is set to true, however no binarizer was passed')

        self.binarizer = binarizer
        self.should_binarize = should_binarize
        self.built_hash = None

    @property
    def out_file(self) -> Path:
        if self._out_file is None:
            if not self.should_binarize:
                raise Exception(repr(self) + ''' 
                    Attempted to access binarized output file, however this instance does not support binarization
                ''')

            self._out_file = self._binarize()

        return self._out_file

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

    def _binarize(self) -> None:
        binarizer = self.binarizer(self.out_dir, self.missions_dir)

        return binarizer.binarize()

    def __hash__(self) -> Any:
        return self.build()

    def build(self) -> Any:
        if self.built_hash is None:
            if self.out_dir.exists():
                shutil.rmtree(self.out_dir)

            self._join_sources()

            if self.should_binarize:
                binarized = self._binarize()

                self.built_hash = hash_file(binarized)
            else:
                if self.out_dir.is_file():
                    raise TypeError(f'Output directory is a file')

                self.built_hash = hash_dir(self.out_dir)

        return self.built_hash
