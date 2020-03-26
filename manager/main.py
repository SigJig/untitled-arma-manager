
import os

from pathlib import Path
from dotenv import load_dotenv

from .builder import Linker, Builder, process_steps
from .clients import SteamCMD, ArmaClient, Service
from .config import config

from .const import (
    DEFAULT_CONFIG_FILE
)

FLAG_CONVERTERS = {
    'r': 'run',
    'b': 'build',
    'i': 'install'
}

def parse_args(iargs: list):
    iter_ = iter(iargs)
    options, args = {}, []

    def add_option(option: str):
        # Todo: add support for values
        if '=' in option:
            k, v = option.split('=')

            options[k] = v
        else:
            options[option] = None

    for i in iter_:
        if i.startswith('-'):
            stripped = i.lstrip('-')
            opt = (i.startswith('--') and stripped) or FLAG_CONVERTERS[stripped]
            
            add_option(opt)
        else:
            args.append(i)

    return args, options

def main(args: list, options: dict):
    config.set_json_file(
        Path(options.get('config', DEFAULT_CONFIG_FILE))
    )

    if 'env' in options:
        load_dotenv(dotenv_path=options['env'])

    # Use False instead of None because options can still be present
    # even if value is None
    if (install := options.get('install', False)) is not False:
        if install is None:
            install = config.services.keys()

        for i in install:
            service = Service.create(i, **config.services[i])

            service.install()

    if (build := options.get('build', False)) is not False:
        if build is None:
            steps = config.steps
        else:
            steps = []
            build = [x.strip() for x in build.split(',')]

            for i in config.steps:
                if i.get('name', None) in build:
                    steps.append(i)

        print('Running {0} steps ({1})'.format(len(steps), ', '.join([x['name'] for x in steps])))
        
        process_steps(steps)

    if ('run' in options): ArmaClient(**config.services['arma3']).run()

def cli(args: list):
    return main(*parse_args(args))
