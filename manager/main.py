
import os
from pathlib import Path
from dotenv import load_dotenv
from .builder import Linker, Builder
from .clients import SteamCMD, ArmaClient

def set_environ(**vars_):
    for k, v in vars_.items():
        os.environ[k] = v

def process_step(step: dict):
    type_ = step.pop('type')
    type_ = type_.lower()

    if type_ == 'link':
        return Linker(**step).run()
    elif type_ == 'build':
        return Builder(step).build()
    else:
        raise Exception(f'Invalid step type {type_}')

def main(opts: dict) -> None:
    for k, v in opts.get('services', {}).items():
        path = Path(v['path'])

        # Todo: make a factory
        service = {
            'steamcmd': SteamCMD,
            'arma3': ArmaClient
        }[k]

        args = {'path': path}
        
        if not service.is_installed(**args):
            service.install(**args)

    if env := opts.get('env'):
        if file := env.get('file', None):
            load_dotenv(dotenv_path=file)
        
        if vars_ := env.get('vars', {}):
            set_environ(**vars_)

    for i in opts.get('steps', []):
        print(i)
        process_step(i)