
import abc
from pathlib import Path, PurePath 
from typing import Tuple, Union, Sequence

U = Union[PurePath, Tuple[PurePath, PurePath]]

# Should yield contents that are passed to the builder which then outputs into the bin dir
class Joiner(abc.ABC):
    @abc.abstractproperty
    def paths(self) -> Sequence[U]: pass

class AYUJoiner(Joiner):
    """
    Simple joiner that follows the AsYetUntitled mission source code structure
    """
    @property
    def paths(self) -> Sequence[U]:
        return [ PurePath('PhoenixRP.Altis') ]
