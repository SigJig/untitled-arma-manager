
import abc
from pathlib import Path, PurePath 
from typing import Tuple, Union, Sequence, List

# Should yield contents that are passed to the builder which then outputs into the bin dir
class Joiner(abc.ABC):
    @abc.abstractproperty
    def paths(self) -> Sequence[Tuple[PurePath, PurePath]]: pass
