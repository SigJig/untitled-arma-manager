
import os, re, json, shutil, functools
from pathlib import Path
from collections import namedtuple
from dotenv import load_dotenv
from manager.armaconfig.config import Config, decode, encode, Encoder

load_dotenv()

CLASSNAME_SHORTCUTS = {
    'ifrit': 'O_MRAP_02_F'
}

PHX_DIR = Path(os.environ['PHOENIX_SOURCE_DIR'])
SKINS_DIR = PHX_DIR.joinpath('skins.githide')

CACHE_DIR = Path(os.environ['CACHE_DIR']).joinpath('missions')

def get_current_mission(name):
    highest = -1

    for _, dirs, _ in os.walk(CACHE_DIR):
        for d in dirs:
            if match := re.match(re.compile(name + '(\\d*)'), d):
                idx = int(match.group(1))

                if idx > highest:
                    highest = idx

    return name + str(highest)

def get_classname(clsname):
    return CLASSNAME_SHORTCUTS.get(clsname, clsname)

""" whitelisted_gangs = Config('CfgWhitelistedGangs')
clothing_store_skins = []

textures = decode(CONFIG_DIR.joinpath('CfgTextures.hpp'))
cfg_textures = textures['CfgTextures']

vehicles = decode(CONFIG_DIR.joinpath('CfgVehicles.hpp'))
cfg_vehicles = vehicles['LifeCfgVehicles']
 """
_Mission = namedtuple('Mission', ['base', 'textures', 'config'])

class Mission(_Mission): #namedtuple('Mission', ['base', 'textures', 'config'])):
    @functools.cached_property
    def cfg_vehicles(self):
        return decode(self.config.joinpath('CfgVehicles.hpp'))

    @functools.cached_property
    def cfg_textures(self):
        return decode(self.config.joinpath('CfgTextures.hpp'))

    @functools.cached_property
    def cfg_whitelist(self):
        return Config('CfgWhitelistedGangs')

    @classmethod
    def current(cls, prefix='mission_'):
        highest = -1

        for _, dirs, _ in os.walk(CACHE_DIR):
            for d in dirs:
                if match := re.match(re.compile(prefix + '(\\d*)'), d):
                    idx = int(match.group(1))

                    if idx > highest:
                        highest = idx

        path = CACHE_DIR.joinpath(prefix + str(highest))

        return cls(path, path.joinpath('data', 'textures'), path.joinpath('PHX', 'Configuration'))

class Entry:
    def __init__(self, path, mission):
        self.path = path
        self.mission = mission

        self.clothes = []

    @functools.cached_property
    def manifest(self):
        with open(self.path.joinpath('manifest.json')) as fp:
            return json.load(fp)

    @property
    def skins_dir(self):
        return self.mission.textures.joinpath(self.manifest['name'].lower())

    def _resolve_skin(self, skin):
        def _resolve(part):
            output = self.skins_dir.joinpath(part)

            shutil.copy(
                self.path.joinpath(part),
                output
            )

            return output

        if not isinstance(skin, list):
            skin = [skin]
        
        return [_resolve(x) for x in skin]

    
    def _rel_tex_path(self, skin, base):
        """
        Helper to get the path of the skin related to the base dir.
        For example, CfgTextures uses paths relative to `data/textures`,
        whereas CfgVehicles uses paths relative to mission root.

        Returns a stringified version of the path, with / being replaced with \\
        """
        return str(os.path.relpath(skin, base)).replace('/', '\\')

    def process(self):
        name = self.manifest['name'].lower()
        in_gang_fnc = "['%s', player] call PHX_fnc_inWhitelistGang" % name

        if not self.skins_dir.exists(): os.mkdir(self.skins_dir)

        self.mission.cfg_whitelist[name] = {
            'gangID': str(self.manifest['id']),
            'displayName': self.manifest['displayName'],
            'clothingShop': name
        }

        for k, v in self.manifest.get('clothing', {}).items():
            classname = get_classname(k)

            self.clothes.append([classname, "Gang Skin", 10000, in_gang_fnc])

            skin = v['skin']
            resolved = self._resolve_skin(skin)

            skin = [self._rel_tex_path(x, self.mission.textures) for x in resolved]

            texture_entry = [skin[0], "_side isEqualTo civilian && " + in_gang_fnc, [1, ""]]
            textures = self.mission.cfg_textures['CfgTextures']

            if classname not in textures:
                textures[classname] = {
                    'textures': [texture_entry]
                }
            else:
                textures[classname]['textures'].append(texture_entry)

        for k, v in self.manifest.get('vehicles', {}).items():
            classname = get_classname(k)
            life_cfg_vehicles = self.mission.cfg_vehicles['lifecfgvehicles']

            assert classname in life_cfg_vehicles, '%s not a valid whip bruh' % classname

            skin = [self._rel_tex_path(x, self.mission.base) for x in self._resolve_skin(v['skin'])]

            life_cfg_vehicles.setdefault(classname, {'textures': {}})
            life_cfg_vehicles[classname]['textures'][name] = {
                'name': self.manifest['displayName'],
                'side': 'reb',
                'skins': v['skin'],
                'condition': in_gang_fnc
            }

def main():
    """
    * [ x ] Add to clothing store
    * [ x ] Add to textures
    * [ x ] Add to vehicle store
    * [ x ] Add to whitelistedgangs
    * [ x ] Move files to dir
    """
    mission = Mission.current()
    entries = []

    for d in os.listdir(SKINS_DIR):
        path = SKINS_DIR.joinpath(d).resolve()

        if not path.is_dir():
            print('Skipping %s as it is not a dir' % d)

        entry = Entry(path, mission)
        entry.process()
        entries.append(entry)

    for path, cfg, include_self in (('CfgTextures.hpp', mission.cfg_textures, False),
                                    ('CfgVehicles.hpp', mission.cfg_vehicles, False),
                                    ('CfgWhitelistedGangs.hpp', mission.cfg_whitelist, True)
                                    ):
        with open(mission.config.joinpath(path), 'w') as fp:
            for x in encode(cfg, include_self=include_self, indent=4):
                fp.write(x)

    with open(mission.config.joinpath('gangs/uniforms.inc.hpp'), 'w') as fp:
        encoder = Encoder(indent=4)

        clothes = []
        for i in entries:
            clothes.extend(i.clothes)

        for x in encoder.encode(clothes):
            fp.write(x)

if __name__ == '__main__':
    main()
