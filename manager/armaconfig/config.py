
import re
from collections import OrderedDict, namedtuple, _OrderedDictItemsView, abc
from .analyser import Parser, NodeType

ValueNode = namedtuple('ValueNode', ['name', 'value'])

class Encoder:
    def __init__(self, indent=None):
        self._indent = indent
        self._indent_lvl = 0

    def _make_indent(self, pre=None, post=None):
        if not self._indent: return

        if pre is not None:
            yield pre

        yield (' ' * self._indent * self._indent_lvl)

        if post is not None:
            yield post

    def _encode_one(self, node):
        if isinstance(node, Config):
            yield 'class %s' % node.name

            if node.inherits:
                yield ':' + node.inherits.name

            yield '{'

            self._indent_lvl += 1

            for x in node.values_raw():
                yield from self._make_indent(pre='\n')
                yield from self._encode_one(x)

            self._indent_lvl -= 1

            yield from self._make_indent('\n', '};\n')
        elif isinstance(node, ValueNode):
            yield node.name

            is_array = isinstance(node.value, (list, tuple))

            if is_array:
                yield '[]'

            yield '='
            yield from self._encode_one(node.value)
            yield ';'
        elif isinstance(node, (list, tuple)):
            yield '{'

            is_first = True
            self._indent_lvl += 1

            for x in node:
                if not is_first:
                    yield ','

                yield from self._make_indent(pre='\n')
                yield from self._encode_one(x)

                is_first = False

            self._indent_lvl -= 1

            yield from self._make_indent('\n', '}')
        elif isinstance(node, str):
            yield '"%s"' % re.sub(r'\"', '""', node)
        elif isinstance(node, bool):
            yield str(int(node))
        else:
            yield str(node)

    def encode(self, node):
        for x in node.values_raw():
            yield from self._encode_one(x)

def encode(node, *args, **kwargs):
    encoder = Encoder(*args, **kwargs)

    return encoder.encode(node)

def decode(unit):
    parser = Parser(unit)
    base_config = Config(unit.name)

    configs = [base_config]

    def _clean_value(value):
        if isinstance(value, list):
            return [_clean_value(x) for x in value if not isinstance(x, str) or x.strip()]
        else:
            value = value.strip()

            try:
                return bool(['false', 'true'].index(value))
            except ValueError:
                pass

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
                config = Config(name, inherits, configs[-1])

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
    def __init__(self, name, inherits=None, parent=None):
        self.name = name
        self.parent = parent

        if inherits:
            try:
                self.inherits = self.parent.get_config(inherits)
            except KeyError:
                raise ValueError('Attempted to inherit non-existing config (%s)' % inherits)
        else:
            self.inherits = None

        self._dict = OrderedDict()

    def add(self, node):
        if node.name in self:
            raise ValueError('%s already defined' % node.name)

        self[node.name] = node

    def get_config(self, k):
        try:
            config = self[k]

            if not isinstance(config, Config):
                raise TypeError()

            return config
        except KeyError:
            if self.parent:
                return self.parent.get_config(k)

            raise

    def items_raw(self):
        for key in self:
            yield key, self._get_raw(key)

    def values_raw(self):
        for key in self:
            yield self._get_raw(key)

    def _get_raw(self, item):
        item = self._keytransform(item)

        try:
            return self._dict[item]
        except KeyError:
            if self.inherits:
                return self.inherits._get_raw(item)

            raise

    def _keytransform(self, key):
        return key.lower()

    def __iter__(self):
        if self.inherits:
            yield from self.inherits
        
        yield from self._dict

    def __getitem__(self, item):
        raw = self._get_raw(item)

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
