
import os
from pathlib import Path, PurePath
from builder import Builder
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

    class LifeJoiner(Joiner):
        @property
        def paths(self):
            return [ (PurePath('Framework', 'Server Side'), PurePath()) ]

    from hashing import hash_dir

    b = Builder(source_dir=MISSION_LOCATION, out_dir=MISSION_BIN, missions_dir=TEST_DIR, joiner=PHXJoiner)
    hsh = b.build()

    a, b = hsh.hexdigest(), hash_dir(TEST_DIR.joinpath('googo')).hexdigest()
    print(a, b, a == b)
