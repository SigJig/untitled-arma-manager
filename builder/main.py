
import os
from pathlib import Path, PurePath
from builder import Builder, PBOPacker
from joiner import Joiner

TEST_DIR = Path.home().joinpath('Documents', 'development', 'clones', 'phoenixrp-altislife')

if not TEST_DIR.exists():
    TEST_DIR.mkdir()

MISSION_LOCATION = TEST_DIR
MISSION_BIN = TEST_DIR.joinpath('bin')
MISSIONS_DIR = TEST_DIR.joinpath('missions')

if __name__ == '__main__':
    class PHXJoiner(Joiner):
        @property
        def paths(self):
            return [ (PurePath('Framework', 'Client Side'), PurePath()), (PurePath('PhoenixRP.Altis'), PurePath()) ]

    b = Builder(source_dir=MISSION_LOCATION,
                out_dir=MISSION_BIN,
                missions_dir=MISSIONS_DIR,
                joiner=PHXJoiner,
                binarizer=PBOPacker,
                should_binarize=True)

    hsh = b.build()

    print(hsh.hexdigest())
