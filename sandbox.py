
import os, sys, shutil, requests, io, platform
from pathlib import Path, PurePath
from manager import Builder, SteamCMD, ArmaClient, print_progress
from pyunpack import Archive

if platform.system() == 'Linux':
    DEV_DIR = Path.home().joinpath('Documents', 'development')
    OUT_DIR = DEV_DIR.joinpath('tests', 'arma-manager-test')
    SOURCE_DIR = DEV_DIR.joinpath('clones', 'phoenixrp-altislife')
else:
    DEV_DIR = Path('F:/Development')
    OUT_DIR = DEV_DIR.joinpath('Testing', 'arma-manager-test')
    SOURCE_DIR = DEV_DIR.joinpath('Clones', 'phoenixrp-altislife')

SERVER_DIR = OUT_DIR.joinpath('server')
INSTALL_DIR = SERVER_DIR.joinpath('arma')
MODS_DIR = INSTALL_DIR.joinpath('mods')

if INSTALL_DIR.exists() and not MODS_DIR.exists(): os.makedirs(MODS_DIR)

CACHE_BASE_DIR = OUT_DIR.joinpath('cache')

CACHE = {
    'missions': CACHE_BASE_DIR.joinpath('missions'),
    'mods': CACHE_BASE_DIR.joinpath('mods'),
    'downloads': CACHE_BASE_DIR.joinpath('downloads')
}

mission_builder = Builder({
    #'source_dir': SOURCE_DIR,
    #'paths': [
    #    PurePath('Framework', 'Client Side'),
    #    PurePath('PhoenixRP.Altis')
    #],
    'source_dir': OUT_DIR.joinpath('test_mission'),
    #'paths': [
    #    PurePath()
    #],
    'output': {
        'tmp_dir': OUT_DIR.joinpath('tmp'),
        'missions_dir': CACHE['missions'],
        'should_binarize': False
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

@print_progress('Installing extDB3')
def install_extdb3():
    # note: 7zip executable is required on path
    r = requests.get('https://bitbucket.org/torndeco/extdb3/downloads/extDB3-1031.7z', stream=True)

    dl_path = CACHE['downloads'].joinpath('extdb3.7z')
    extract_path = CACHE['mods'].joinpath('extDB3')

    for i in (CACHE['downloads'], extract_path):
        if not i.exists():
            os.makedirs(i)

    with open(dl_path, 'wb') as fp:
        for chunk in r.iter_content(16 * 1024):
            fp.write(chunk)

    Archive(dl_path).extractall(extract_path)

    extdb3_path = MODS_DIR.joinpath('@extDB3')

    if extdb3_path.exists(): shutil.rmtree(extdb3_path)

    os.symlink(extract_path.joinpath('@extDB3'), extdb3_path)

    if platform.system() == 'Linux':
        mallocs = ('tbbmalloc.so',)
    else:
        mallocs = ('tbbmalloc.dll', 'tbbmalloc_x64.dll')

    for i in mallocs:
        src, dst = extract_path.joinpath(i), INSTALL_DIR.joinpath(i)

        if dst.exists(): os.remove(dst)

        os.symlink(src, dst)

@print_progress('Building missions')
def build():
    mission_builder.build()
    #life_builder.build()

#@print_progress('Installing required services')
def install():
    if not SteamCMD.is_installed(SERVER_DIR):
        SteamCMD.install(SERVER_DIR)

    ArmaClient.install(
        login=[x.strip() for x in open('credentials.env').readlines()],
        validate=True,
        path=INSTALL_DIR,
        steam_path=SERVER_DIR
    )

@print_progress('Launching server')
def run():
    os.chdir(INSTALL_DIR)

    ArmaClient(
        path=INSTALL_DIR,
        config='config.cfg',
        profiles='profiles',
        mods={
            'dir': MODS_DIR,
            'load': ['@life_server',  '@extDB3']
        }
    ).run()

@print_progress('Creating symlinks')
def create_symlink():
    links = [
        (
            mission_builder.current_mission,
            INSTALL_DIR.joinpath('mpmissions', 'PhoenixRP.Altis.pbo'),
            #Path('C:/Users/sigmu/AppData/Local/Arma 3/MPMissionsCache/PhoenixRP.Altis.pbo')
        ),
        (
            life_builder.current_mission,
            INSTALL_DIR.joinpath('mods', '@life_server', 'addons', 'life_server.pbo')
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
if 'ie' in flags: install_extdb3()
if 'b' in flags: build()
if 'l' in flags: create_symlink()
if 'r' in flags: run()