
from __future__ import annotations

import io, os, requests, platform, zipfile, tarfile, subprocess

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

class SteamCMD:
    uri = 'https://steamcdn-a.akamaihd.net/client/installer/'
    filenames = {
        'windows': 'steamcmd.zip',
        'linux': 'steamcmd_linux.tar.gz'
    }
    stream_chunk_size = 8 * 1024
    default_install_dir = Path.home().joinpath('steamcmd')

    def __init__(self, path: Path = None) -> SteamCMD:
        path = path or type(self).default_install_dir

        if path.is_dir():
            self.path = path.joinpath('steamcmd.sh' if platform.system() == 'Linux' else 'steamcmd.exe')
        else:
            self.path = path

        self.args = []

    def run(self):
        callable_ = self.subprocess_callable

        subprocess.check_call(callable_)

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
    def subprocess_callable(self) -> Sequence[str]:
        res = [self.path]
        res += ['{}'.format(' '.join(x)) for x in self.args]

        return res + [self._format_arg('quit')]

    def _format_arg(self, arg: str) -> str:
        return '+' + arg

    @classmethod
    def is_installed(cls, path: Path) -> bool:
        return path.exists() and bool(os.listdir(path))

    @classmethod
    def install(cls, path: Path, force: bool = False, delete_tmp_file: bool = True) -> Type[SteamCMD]:
        cls.default_install_dir = path

        if cls.is_installed(path) and not force: return

        try:
            system_os = platform.system().lower()

            filename = cls.filenames[system_os]
        except KeyError:
            raise Exception(f'Unsupported platform {system_os}')
        else:
            uri = cls.uri + filename
            r = requests.get(uri, stream=True)

            if not path.exists():
                os.makedirs(path)

            mem_file = io.BytesIO(r.content)

            if system_os == 'linux':
                file_obj = tarfile.TarFile.open(fileobj=mem_file)
            else:
                file_obj = zipfile.ZipFile(mem_file)
            
            file_obj.extractall(path)

        return cls

    @classmethod
    def uninstall(cls, path: Path) -> Type[SteamCMD]:
        if not path.exists(): return

        os.rmdir(path)

        return cls

class ArmaClient:
    steam_game_id = '233780'

    def __init__(self, **opts):
        self._opts = opts
        self.path = self._opts.pop('path')
        self.cli_args = []

        self.add_arg(*self._opts.items())

    def run(self):
        subprocess.check_call(self.subprocess_callable, cwd=self.path.parent)

    def add_arg(self, *args: Sequence[Union[str, Tuple[str, str]]]):
        self.cli_args.extend(args)

        return self

    @property
    def subprocess_callable(self) -> Sequence[str]:
        return [self.path] + [
            self._format_arg(*x) if type(x) in [list, tuple] else self._format_arg(x) for x in self.cli_args
        ]

    def _format_arg(self, name: str, value: Union[str, None] = None) -> str:
        name = '-' + name

        if value is not None:
            return name + '=' + str(value)

        return name

    @classmethod
    def install(cls, login: Tuple[str, str], validate: bool = True, path: Path = None) -> Type[ArmaClient]:
        cmd_arr = ['app_update', cls.steam_game_id]

        if validate:
            cmd_arr.append('validate')

        steamcmd = SteamCMD().login(*login)

        if path is not None:
            if path.exists():
                if not path.is_dir():
                    raise FileExistsError(path)
                elif os.listdir(path):
                    raise Exception(f'Directory "{path}" is not empty')

            steamcmd.add(['force_install_dir', os.fspath(path.absolute())])

        steamcmd.add(cmd_arr).run()

        return cls