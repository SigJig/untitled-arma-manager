
import os
import abc
import json
import shutil
from typing import (
    Type,
    Any,
    List,
    Union
)
from pathlib import Path, PurePath
from pboutil import PBOFile
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

BINARIZERS = {
    'pbopacker': PBOPacker
}

class BuilderOptions:
    _default_output = {
        'binarizer': PBOPacker,
        'should_binarize': True,
        'tmp_dir': 'tmp',
        'missions_dir': 'missions'
    }

    def __init__(self, **opts) -> None:
        self.opts = opts
        self.output = {
            **self._default_output,
            **opts.get('output', {})
        }

        if not 'source_dir' in self.opts:
            raise Exception('Missing source_dir')

        self.source_dir = self.opts['source_dir']
        self._paths = opts.get('paths', [])

        if self.output.get('should_binarize'):
            if bnzr := self.output.get('binarizer', ''):
                try:
                    if not isinstance(bnzr, Binarizer) and not issubclass(bnzr, Binarizer):
                        print(type(bnzr))
                        bnzr = BINARIZERS[bnzr]
                    
                    self.output['binarizer'] = bnzr
                except KeyError:
                    raise Exception(f'Invalid binarizer {bnzr}')
            else:
                raise Exception('Invalid binarizer')

    def _process_pure_path(self, path: Union[PurePath, List[str], str]):
        if isinstance(path, PurePath): return path

        if isinstance(path, list):
            return PurePath(*path)

        return PurePath(path)

    def _process_path(self, path: Union[PurePath, List[str], str]):
        pure = self._process_pure_path(path)

        # TODO: If the pure path is relative, it should join with the source_dir
        return self.source_dir.joinpath(pure)

    @property
    def should_binarize(self) -> bool:
        return self.output['should_binarize']

    @property
    def binarizer(self) -> Binarizer:
        return self.output['binarizer']

    @property
    def tmp_dir(self) -> Path:
        return self._process_path(self.output['tmp_dir'])

    @property
    def missions_dir(self) -> Path:
        return self._process_path(self.output['missions_dir'])

    @property
    def paths(self) -> List[Any]:
        if not self._paths: return []

        for p in self._paths:
            src, dst = self._process_pure_path(p[0]), self._process_pure_path(p[1]) if len(p) > 1 else None

            yield src, dst

    @classmethod
    def from_json(cls, file: Path) -> Any:
        with open(file) as fp:
            return cls(**json.load(fp))

# Possibly a user-defined class that sets instructions on how to compile the source files?
# Option to pass custom packager (for example if you wanted to use a different PBO packer or ObfuSQF)
class Builder:
    def __init__(self, 
            opts: Union[dict, BuilderOptions]
        ) -> None:

        if not isinstance(opts, BuilderOptions):
            opts = BuilderOptions(**opts)

        self.opts = opts
        
        self._out_file = None
        self.built_hash = None

    def __del__(self):
        """
        if self.opts and self.opts.tmp_dir.exists():
            shutil.rmtree(self.opts.tmp_dir)
        """

    @property
    def out_file(self) -> Path:
        if self._out_file is None:
            if not self.opts.should_binarize:
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
        self._verify_dir(self.opts.tmp_dir)

        for src_pure, dst_pure in self.opts.paths:

            # pylint: disable=unsubscriptable-object
            src = self.opts.source_dir.joinpath(src_pure)

            if src.is_file():
                dst = self.opts.tmp_dir.joinpath(
                    dst_pure
                        if dst_pure is not None
                        else 
                    src.name
                )
            elif dst_pure is not None:
                dst = self.opts.tmp_dir.joinpath(dst_pure)
            else:
                dst = self.opts.tmp_dir

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
        binarizer = self.opts.binarizer(self.opts.tmp_dir, self.opts.missions_dir)

        return binarizer.binarize()

    def __hash__(self) -> Any:
        return self.build()

    def build(self) -> Any:
        if self.built_hash is None:
            if self.opts.tmp_dir.exists():
                shutil.rmtree(self.opts.tmp_dir)

            self._join_sources()

            if self.opts.should_binarize:
                binarized = self._binarize()

                self.built_hash = hash_file(binarized)
            else:
                if self.opts.out_dir.is_file():
                    raise TypeError(f'Output directory is a file')

                self.built_hash = hash_dir(self.opts.tmp_dir)

        return self.built_hash
