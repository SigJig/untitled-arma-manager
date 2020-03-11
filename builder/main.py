
import os
from pathlib import Path, PurePath
from builder import Builder, PBOPacker

TEST_DIR = Path.home().joinpath('Documents', 'development', 'clones', 'phoenixrp-altislife')

"""{
    "source_dir": [""],
    "paths": [
        [["Framework", "Client Side"]],
        ["PhoenixRP.Altis"]
    ],
    "output": {
        "binarize": true,
        "binarizer": "pbopacker",
        "tmp_dir": "",
        "missions_dir": ""
    }
}"""

if __name__ == '__main__':
    b = Builder({
        'source_dir': TEST_DIR,
        'paths': [
            [["Framework", "Client Side"]],
            ["PhoenixRP.Altis"]
        ]
    })

    hsh = b.build()

    print(hsh.hexdigest())
