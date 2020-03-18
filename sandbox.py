
import os, sys
from pathlib import Path, PurePath
from manager import Builder, SteamCMD, ArmaClient

DEV_DIR = Path('F:/Development')
OUT_DIR = DEV_DIR.joinpath('Testing', 'arma-manager-test')

SERVER_DIR = OUT_DIR.joinpath('server')
INSTALL_DIR = SERVER_DIR.joinpath('arma')

data = {
    'source_dir': DEV_DIR.joinpath('Clones', 'phoenixrp-altislife'),
    'paths': [
        PurePath('Framework', 'Client Side'),
        PurePath('PhoenixRP.Altis')
    ],
    'output': {
        'tmp_dir': OUT_DIR.joinpath('tmp'),
        'missions_dir': OUT_DIR.joinpath('missions'),
        'should_binarize': False
    }
}

builder = Builder(data)

def build():
    builder.build()

def install(args):
    if not SteamCMD.is_installed(SERVER_DIR):
        SteamCMD.install(SERVER_DIR)

        ArmaClient.install(login=args, path=INSTALL_DIR)

def run():
    ArmaClient(path=INSTALL_DIR).run()

def create_symlink():
    mpmissions = INSTALL_DIR.joinpath('mpmissions')
    f = mpmissions.joinpath('PhoenixRP.Altis')

    if f.exists(): os.remove(f)

    os.symlink(builder.current_mission, f)

flags = []
args = []

for i in sys.argv[1:]:
    if i.startswith('-'): flags.append(i.lstrip('-'))
    else: args.append(i)

if 'b' in flags: build()
if 'i' in flags: install(args)
if 'r' in flags: run()
if 'l' in flags: create_symlink()