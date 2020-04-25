
import re
from collections import OrderedDict, namedtuple, _OrderedDictItemsView, abc
from .analyser import Parser, NodeType

ValueNode = namedtuple('ValueNode', ['name', 'value'])

def encode(node):
    if isinstance(node, Config):
        yield 'class %s' % node.name

        if node.inherits:
            yield ':' + node.inherits.name

        yield '{'
        yield from (encode(x) for x in node)
        yield '};'
    elif isinstance(node, ValueNode):
        yield node.name

        is_array = isinstance(node.value, (list, tuple))

        if is_array:
            yield '[]'

        yield '='
        yield from encode(node.value)
        yield ';'
    elif isinstance(node, (list, tuple)):
        yield '{'
        yield from (encode(x) for x in node)
        yield '}'
    else:
        yield re.sub(r'\"', '""', str(node))

def decode(unit):
    parser = Parser(unit)
    base_config = Config(unit.name)

    configs = [base_config]

    def _clean_value(value):
        if isinstance(value, list):
            return [_clean_value(x) for x in value if (isinstance(x, list) or not isinstance(x, str) or x.strip())]
        else:
            value = value.strip()

            if boolean := next((x for x in ('true', 'false') if x == value), None) is not None:
                return boolean

            # TODO: Maybe move this to its own function, as it can be used in the preprocessor's include statement
            if value and value[0] == '"' and value[-1] == '"':
                value = value[1:len(value) - 1]

            try:
                new_val = float(value)

                if new_val.is_integer():
                    new_val = int(new_val)

                return new_val
            except ValueError:
                return value

    def _decode_iter(iterator):
        for nodetype, nodeargs in iterator:
            if nodetype == NodeType.CLASS:
                name, inherits, iter_ = nodeargs
                config = Config(name, inherits)

                configs[-1].add(config)
                configs.append(config)

                _decode_iter(iter_)
            elif nodetype == NodeType.PROPERTY:
                name, value = nodeargs

                configs[-1].add(ValueNode(name, _clean_value(value)))

        configs.pop()

    _decode_iter(parser.parse())

    return base_config

class Config(abc.MutableMapping, dict):
    """
    A `Config` object acts as a proxy to an ordered dict.
    The dict contains the keys and values that the config consists of.

    It's purpose is to 

    For example, consider the following Arma 3 Config class:

    class MyClass {
        string_value = "This is a string";
        array_value[] = {"This", "is", "an", "array};
    };

    When the above is represented as a dictionary,
    it would look something like this:

    {
        'MyClass': {
            'string_value': 'This is a string',
            'array_value': ['This', 'is', 'an', 'array']
        }
    }
    """
    def __init__(self, name, inherits=None):
        self.name = name
        self.inherits = inherits
        self._dict = OrderedDict()

    def __iter__(self):
        if self.inherits:
            yield from self.inherits
        
        yield from self._dict

    def __getitem__(self, item):
        item = self._keytransform(item)

        try:
            raw = self._dict[item]
        except KeyError:
            if self.inherits:
                return self.inherits[item]

            raise
        else:
            if isinstance(raw, ValueNode):
                return raw.value

            return raw

    def __setitem__(self, item, value):
        if not isinstance(value, (Config, ValueNode)):
            value = ValueNode(item, value)

        self._dict[self._keytransform(item)] = value

    def __delitem__(self, item):
        del self._dict[self._keytransform(item)]

    def __len__(self):
        return len(self._dict)

    def _keytransform(self, key):
        return key.lower()

    def add(self, node):
        if node.name in self:
            raise ValueError('%s already defined' % node.name)

        self[node.name] = node