
import os, sys, shutil, requests, io, platform
from pathlib import Path, PurePath
from manager import Builder, SteamCMD, ArmaClient, print_progress, main
from pyunpack import Archive

def install_extdb3():
    """     # note: 7zip executable is required on path
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

        os.symlink(src, dst) """

""" def run():
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
 """
flags = []
args = []

import json
main(json.load(open('example.githide.json')))