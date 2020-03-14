
from __future__ import annotations

import io, os, requests, platform, zipfile, tarfile, subprocess

from pathlib import (
    Path,
    PurePath
)
from typing import (
    Sequence,
    Union,
    Type
)

class SteamCMD:
    uri = 'https://steamcdn-a.akamaihd.net/client/installer/'
    filenames = {
        'windows': 'steamcmd.zip',
        'linux': 'steamcmd_linux.tar.gz'
    }
    stream_chunk_size = 8 * 1024

    def __init__(self, path: Path) -> SteamCMD:
        if path.is_dir():
            self.path = path.joinpath('steamcmd.sh' if platform.system() == 'Linux' else 'steamcmd.exe')
        else:
            self.path = path

        self.args = []

    def run(self):
        subprocess.check_call(self.subprocess_callable)

    def add(self, *commands: Sequence[Union[str, list]]) -> SteamCMD:
        for command in self._construct(*commands):
            self.args.append(command)

        return self

    def login(self, username, password, code=None) -> SteamCMD:
        cmd_arr = ['login', username, password]
        
        if code is not None:
            cmd_arr.append(code)

        return self.add(cmd_arr)

    @property
    def subprocess_callable(self) -> Sequence[str]:
        res = [self.path]
        res += ['"{}"'.format(' '.join(x)) for x in self.args]

        return res + [self._format_cmd('quit')]

    def _construct(self, *commands: Sequence[Union[str, list]]) -> None:
        for command in commands:
            if isinstance(command, list):
                if len(command) > 1:
                    key, args = command[0], command[1:]

                    yield [self._format_cmd(key)] + args if isinstance(args, list) else [args]
                else:
                    command = command[0]
            else:
                yield [self._format_cmd(command)]

    def _format_cmd(self, command: str) -> str:
        return '+' + command

    @classmethod
    def is_installed(cls, path: Path) -> bool:
        return path.exists() and bool(os.listdir(path))

    @classmethod
    def install(cls, path: Path, delete_tmp_file: bool = True) -> Type[SteamCMD]:
        if cls.is_installed(path): return

        try:
            system_os = platform.system().lower()

            filename = cls.filenames[system_os]
        except KeyError:
            raise Exception(f'Unsupported platform {system_os}')
        else:
            uri = cls.uri + filename
            r = requests.get(uri, stream=True)

            _zip_path = path.joinpath(filename)
            with open(_zip_path, 'wb') as fp:
                for chunk in r.iter_content(chunk_size=cls.stream_chunk_size):
                    fp.write(chunk)

            if system_os == 'linux':
                file_obj = tarfile.TarFile.open(_zip_path)
            else:
                file_obj = zipfile.ZipFile(_zip_path)
            
            file_obj.extractall(path)

            if delete_tmp_file: os.remove(_zip_path)

        return cls

    @classmethod
    def uninstall(cls, path: Path) -> Type[SteamCMD]:
        if not path.exists(): return

        os.rmdir(path)

        return cls

class ArmaClient:
    steam_game_id = 233780

    @classmethod
    def install(cls, validate: bool = True) -> ArmaClient:
        pass

if __name__ == '__main__':
    import os

    install_path = Path('/opt', 'steamcmd')
    print(os.fspath(install_path))

    if not install_path.exists(): os.makedirs(install_path)

    SteamCMD.install(install_path)
    
    s = SteamCMD(install_path)
    s.login('user', 'password')
    s.run()

