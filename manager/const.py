
import platform

IS_LINUX = platform.system() == 'Linux'

DEFAULT_CONFIG_FILE = 'example.githide.json'

STEAM_DL_URL = 'https://steamcdn-a.akamaihd.net/client/installer/'
STEAM_DL_FILE = 'steamcmd_linux.tar.gz' if IS_LINUX else 'steamcmd.zip'
STEAM_EXECUTABLE = 'steamcmd.sh' if IS_LINUX else 'steamcmd.exe'

ARMA_STEAM_ID = '233780'