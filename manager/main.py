
import os
from pathlib import Path, PurePath
from builder import Builder, BuilderOptions, PBOPacker

json_ = """
{
    "source_dir": "/home/sig/Documents/development/clones/phoenixrp-altislife",
    "paths": [
        [["Framework", "Client Side"]],
        ["PhoenixRP.Altis"]
    ],
    "output": {
        "filename": "mission.Altis"
    }
}
"""

if __name__ == '__main__':
    opts = BuilderOptions.from_json(json_, False)
    b = Builder(opts)

    hsh = b.build()

    
    mission_path = Path.home().joinpath('Documents', 'a3server', 'steamcmd', 'arma3', 'mpmissions')

    dir_, filename = b.opts.missions_dir, b.opts.filename
    os.symlink(dir_.joinpath(filename), mission_path.joinpath(filename))

    print(hsh.hexdigest())
