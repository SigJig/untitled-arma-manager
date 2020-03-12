
import os
from pathlib import Path, PurePath
from builder import Builder, BuilderOptions, PBOPacker

json_ = """
{
    "source_dir": "/home/sig/Documents/development/clones/phoenixrp-altislife",
    "paths": [
        [["Framework", "Client Side"]],
        ["PhoenixRP.Altis"]
    ]
}
"""

if __name__ == '__main__':
    opts = BuilderOptions.from_json(json_, False)
    b = Builder(opts)

    hsh = b.build()

    print(hsh.hexdigest())
