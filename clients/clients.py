
import os
import urllib
import platform
from zipfile import (
    ZipFile,
    Path as ZipPath
)
from pathlib import Path, PurePath

STEAM_CMD_URI = 'https://steamcdn-a.akamaihd.net/client/installer/'
STEAM_CMD_FILENAMES = {
    'windows': 'steamcmd.zip',
    'linux': 'steamcmd_linux.tar.gz'
}

class SteamCMD:
    @classmethod
    def is_installed(cls, path: Path):
        return path.exists()

    @classmethod
    def install(cls, path: Path):
        if cls.is_installed(path): return

        try:
            system_os = platform.system().lower()

            filename = STEAM_CMD_FILENAMES[system_os]
        except KeyError:
            raise Exception(f'Unsupported platform {system_os}')
        else:
            uri = STEAM_CMD_URI + filename
