
import os, sys
from pathlib import Path, PurePath
from manager import Builder, SteamCMD, ArmaClient

DEV_DIR = Path('F:/Development')
OUT_DIR = DEV_DIR.joinpath('Testing', 'arma-manager-test')

SERVER_DIR = OUT_DIR.joinpath('server')
INSTALL_DIR = SERVER_DIR.joinpath('arma')

SOURCE_DIR = DEV_DIR.joinpath('Clones', 'phoenixrp-altislife')
CACHE_BASE_DIR = OUT_DIR.joinpath('cache')

CACHE = {
    'missions': CACHE_BASE_DIR.joinpath('missions'),
    'mods': CACHE_BASE_DIR.joinpath('mods')
}

mission_builder = Builder({
    'source_dir': SOURCE_DIR,
    'paths': [
        PurePath('Framework', 'Client Side'),
        PurePath('PhoenixRP.Altis')
    ],
    'output': {
        'tmp_dir': OUT_DIR.joinpath('tmp'),
        'missions_dir': CACHE['missions']
    }
})

life_builder = Builder({
    'source_dir': SOURCE_DIR,
    'paths': [
        PurePath('Framework', 'Server Side', 'life_server')
    ],
    'output': {
        'missions_dir': CACHE['mods'],
        'filename': '@life_server',
        'tmp_dir': OUT_DIR.joinpath('tmp__')
    }
})

def build():
    print('Building mission...')
    mission_builder.build()

    print('Building @life_server...')
    life_builder.build()

def install():
    if not SteamCMD.is_installed(SERVER_DIR):
        SteamCMD.install(SERVER_DIR)

    ArmaClient.install(
        login=[x.strip() for x in open('credentials.env').readlines()],
        validate=True,
        path=INSTALL_DIR,
        steam_path=SERVER_DIR
    )

def run():
    ArmaClient(
        path=INSTALL_DIR,
        config='config.cfg',
        profiles='profiles',
        mods={
            'dir': INSTALL_DIR.joinpath('mods'),
            'load': ['@life_server',  '@extDB3']
        }
    ).run()

def create_symlink():
    links = [
        (
            mission_builder.current_mission,
            INSTALL_DIR.joinpath('mpmissions', 'PhoenixRP.Altis.pbo'),
            Path('C:/Users/sigmu/AppData/Local/Arma 3/MPMissionsCache/PhoenixRP.Altis.pbo')
        ),
        (
            life_builder.current_mission,
            INSTALL_DIR.joinpath('mods', '@life_server', 'Addons', 'life_server.pbo')
        )
    ]

    for x in links:
        src, dst = x[0], x[1:]

        for i in dst:
            if i.exists(): os.remove(i)

            os.symlink(src, i)

flags = []
args = []

for i in sys.argv[1:]:
    if i.startswith('-'): flags.append(i.lstrip('-'))
    else: args.append(i)

if 'i' in flags: install()
if 'b' in flags: build()
if 'l' in flags: create_symlink()
if 'r' in flags: run()