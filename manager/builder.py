
import os, re, abc, json, shutil, collections

from typing import (
    Type,
    Any,
    List,
    Union
)
from pathlib import Path, PurePath
from pboutil import PBOFile
from .hashing import hash_dir, hash_file

class Binarizer(abc.ABC):
    def __init__(self, path: Path, out_path: Path) -> None:
        self.path = path
        
        """ if not out_path.is_file():
            raise Exception(f'Output {out_path} is not a file')
         """
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
        'missions_dir': 'missions',
        'filename': 'mission'
    }

    def __init__(self, **opts) -> None:
        self.opts = opts
        self.output = {
            **self._default_output,
            **opts.get('output', {})
        }

        if not 'source_dir' in self.opts:
            raise Exception('Missing source_dir')

        self.source_dir = self._process_path(self.opts['source_dir'])
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

        if pure.is_absolute():
            return Path(pure)

        return self.source_dir.joinpath(pure)

    @property
    def filename(self) -> str:
        try:
            return self.output['filename']
        except KeyError:
            raise Exception('Filename is not present')

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
            if isinstance(p, collections.Sequence) and not isinstance(p, str) and len(p) > 1:
                src, dst = self._process_pure_path(p[0]), self._process_pure_path(p[1])

                yield src, dst
            else:
                yield self._process_pure_path(p), None

    @classmethod
    def from_json(cls, json_: Union[str, Path], is_file: bool = True) -> Any:
        data = {}

        if is_file:
            with open(json_) as fp:
                data = json.load(fp)
        else:
            data = json.loads(json_)

        return cls(**data)

# Possibly a user-defined class that sets instructions on how to compile the source files?
# Option to pass custom packager (for example if you wanted to use a different PBO packer or ObfuSQF)
class Builder:
    def __init__(self, 
            opts: Union[dict, BuilderOptions]
        ) -> None:

        if not isinstance(opts, BuilderOptions):
            opts = BuilderOptions(**opts)

        self.opts = opts
        
        self._mission_prefix = self.opts.filename + '_'

        self._out_file = None
        self.built_hash = None

    @property
    def out_file(self) -> Path:
        if self._out_file is None:
            if not self.opts.should_binarize:
                raise Exception(repr(self) + ''' 
                    Attempted to access binarized output file, however this instance does not support binarization
                ''')

            self._out_file = self._binarize()

        return self._out_file

    @property 
    def current_mission_idx(self) -> int:
        highest = -1
        for f in self.opts.missions_dir.glob(f'{self._mission_prefix}[0-9]*'):
            if (match := re.match(re.compile(f'{self._mission_prefix}([0-9]+)'), f.name)):
                num_parsed = int(match.group(1))

                if num_parsed > highest:
                    highest = num_parsed

        return highest

    @property
    def next_mission_idx(self) -> int:
        idx = self.current_mission_idx

        return idx + 1

    @property
    def current_mission_name(self) -> str:
        return self._mission_prefix + str(self.current_mission_idx)

    @property
    def next_mission_name(self) -> str:
        return self._mission_prefix + str(self.next_mission_idx)

    @property
    def current_mission(self) -> str:
        return self.opts.missions_dir.joinpath(self.current_mission_name)

    @property
    def next_mission(self) -> str:
        return self.opts.missions_dir.joinpath(self.next_mission_name)

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
        mission_name = self.next_mission_name + '.pbo'
        binarizer = self.opts.binarizer(self.opts.tmp_dir, self.opts.missions_dir.joinpath(mission_name))

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
                if self.opts.missions_dir.is_file():
                    raise TypeError(f'Output directory is a file')

                shutil.copytree(
                    self.opts.tmp_dir,
                    self.opts.missions_dir.joinpath(self.next_mission_name)
                )

                self.built_hash = hash_dir(self.opts.tmp_dir)

        return self.built_hash
