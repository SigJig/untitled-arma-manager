
from __future__ import annotations

import io, os, abc, time, shutil, signal, requests, platform, zipfile, tarfile, subprocess

from pathlib import (
    Path,
    PurePath
)
from typing import (
    Sequence,
    Union,
    Type,
    Tuple,
    List
)

from .config import config

from .const import (
    IS_LINUX,
    STEAM_DL_FILE,
    STEAM_DL_URL,
    STEAM_EXECUTABLE,
    ARMA_STEAM_ID
)

class Service(abc.ABC):
    path: Path = Path()

    @abc.abstractproperty
    def name(self) -> str: pass

    @abc.abstractmethod
    def install(self): pass

    def is_installed(self):
        path = self.path

        if not isinstance(self.path):
            path = Path(self.path)

        return path.exists() and bool(os.listdir(path))

    @classmethod
    def create(cls, to_create: str, *args, **kwargs) -> Service:
        # TODO: This only works for direct subclasses
        for i in cls.__subclasses__():
            if i.name == to_create:
                return i(*args, **kwargs)

        raise Exception(f'Invalid service {to_create}')

class SteamCMD(Service):
    name = 'steamcmd'

    def __init__(self, path: Path, login: list = []) -> SteamCMD:
        self.path = path
        self.args = []

        if not isinstance(self.path, Path):
            self.path = Path(self.path)

        if not self.path.is_dir():
            self.path = self.path.parent
        
        if login:
            self.login(*login) # pylint: disable=no-value-for-parameter

    def run(self):
        callable_ = self.subprocess_callable

        # For some reason installing using steamcmd does not return 0
        subprocess.run(callable_)

    def add(self, *commands: Sequence[Union[str, list]]) -> SteamCMD:
        for command in commands:
            if isinstance(command, list):
                if len(command) > 1:
                    key, args = command[0], command[1:]

                    self.args.append([self._format_arg(key)] + args if isinstance(args, list) else [args])
                else:
                    command = command[0]
            else:
                self.args.append([self._format_arg(command)])

        return self

    def login(self, username: str, password: str, code: Union[str, None] = None) -> SteamCMD:
        cmd_arr = ['login', username, password]
        
        if code is not None:
            cmd_arr.append(code)

        return self.add(cmd_arr)

    @property
    def executable(self) -> Path:
        return self.path.joinpath(STEAM_EXECUTABLE)

    @property
    def subprocess_callable(self) -> Sequence[str]:
        res = [self.executable]
        res += ['{}'.format(' '.join(x)) for x in self.args]

        return res + [self._format_arg('quit')]

    def _format_arg(self, arg: str) -> str:
        return '+' + arg

    def install(self) -> SteamCMD:
        self.uninstall()

        url = STEAM_DL_URL + STEAM_DL_FILE
        r = requests.get(url, stream=True)

        if not self.path.exists():
            os.makedirs(self.path)

        mem_file = io.BytesIO(r.content)

        if IS_LINUX:
            file_obj = tarfile.TarFile.open(fileobj=mem_file)
        else:
            file_obj = zipfile.ZipFile(mem_file)
        
        file_obj.extractall(self.path)

        return self

    def uninstall(self) -> SteamCMD:
        if not self.path.exists(): return

        shutil.rmtree(self.path)

        return self

class ArmaClient(Service):
    name = 'arma3'
    popen: subprocess.Popen = None

    def __init__(self, **opts):
        self._opts = opts
        self.path = self._opts.pop('path')

        if not isinstance(self.path, Path):
            self.path = Path(self.path)

        self._mods = self._opts.pop('mods', {})
        self._loaded_mods = []
        self.cli_args = []

        if self._mods:
            dir_ = PurePath(self.mods.get('dir', 'mods'))

            if not dir_.is_absolute():
                self._mods['dir'] = self.path.joinpath(dir_)
            else:
                self._mods['dir'] = Path(dir_)

        self.add_arg(*self._opts.items())

    def __del__(self):
        self.kill()

    def run(self):
        if self.popen is not None:
            self.kill()

        self.popen = subprocess.Popen(self.subprocess_callable, cwd=self.path)

        self.popen.wait()

    def kill(self):
        if self.popen is not None or self.popen.poll() is None:
            self.popen.terminate()

        self.popen = None

    def add_arg(self, *args: Sequence[Union[str, Tuple[str, str]]]):
        self.cli_args.extend(args)

        return self

    def load_mods(self) -> None:
        path = self.mods['dir']

        for i in self.mods.get('load', []):
            if isinstance(i, Path) and i.is_absolute():
                self._loaded_mods.append(str(i))
            elif (joined := path.joinpath(i)).exists():
                self._loaded_mods.append(str(joined))
            else:
                raise Exception('Invalid mod ' + i)

    @property
    def mods(self) -> dict:
        if self._mods: return self._mods

        raise Exception('Mods not specified')

    @property
    def executable(self) -> str:
        if IS_LINUX:
            exe = 'arma3server'
        elif self._opts.get('64bit', False):
            exe = 'arma3server_x64.exe'
        else:
            exe = 'arma3server.exe'

        return self.path.joinpath(exe)

    @property
    def subprocess_callable(self) -> Sequence[str]:
        try:
            self.load_mods()
        except:
            pass
        else:
            if self._loaded_mods:
                self.add_arg(['mod', ';'.join(self._loaded_mods) + ';'])

        return [self.executable] + [
            self._format_arg(*x) if type(x) in [list, tuple] else self._format_arg(x) for x in self.cli_args
        ]

    def _format_arg(self, name: str, value: Union[str, None] = None) -> str:
        name = '-' + name

        if value is not None:
            return name + '=' + str(value)

        return name

    def install(self) -> ArmaClient:
        cmd_arr = ['app_update', ARMA_STEAM_ID, 'validate']

        steamcmd = SteamCMD(**config.services['steamcmd'])

        if self.path is not None:
            if self.path.exists():
                if not self.path.is_dir():
                    raise TypeError(self.path + ' is a file')

            steamcmd.add(['force_install_dir', os.fspath(self.path.absolute())])

        steamcmd.add(cmd_arr).run()

        return self
