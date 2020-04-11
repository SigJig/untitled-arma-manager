
import re, os, enum, functools, collections

from pathlib import Path
from typing import (
    Any,
    Union,
    Sequence
)

from armaconfig.parser import Parser
from armaconfig.configtypes import to_dict

if __name__ == '__main__':
    import json

    parser = Parser(Path.cwd().joinpath('config.githide.cfg'))

    with open('output.githide.json', 'w') as fp:
        parsed = list(parser.parse())
        dictified = to_dict(parsed)

        print(dictified)
        json.dump(dictified, fp, indent=4)

    print(parser.defined) 

    """with open(Path.cwd().joinpath('config.githide.cfg')) as fp:
        scanner = Scanner(fp)

        for _ in range(30):
            try:
                print(next(scanner.scan()))
            except StopIteration:
                break"""