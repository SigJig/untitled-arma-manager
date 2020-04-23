
import re

def to_dict(data):
    dict_ = {}

    for i in data:
        if hasattr(i, 'to_dict'):
            dict_[i.name] = i.to_dict()
        else:
            dict_[i.name] = i.value

    return dict_

def encode(data):
    for i in data:
        yield from i.encode()

class A3Class:
    def __init__(self, name, inherits, body):
        self.name = name
        self.body = body
        
        if inherits is not None:
            self.inherits = None
        else:
            self.inherits = None

    def to_dict(self):
        dict_ = to_dict(self.body)

        if self.inherits:
            return {
                **self.inherits.to_dict(),
                **dict_
            }

        return dict_

    def __getitem__(self, item):
        try:
            return next(x for x in self.body if x.name == item)
        except StopIteration:
            if not self.inherits:
                raise KeyError(item)

            return self.inherits.__getitem__(item)

    def encode(self):
        yield f'class {self.name}'

        if self.inherits:
            yield f': {self.inherits.name}'

        yield '{'
        yield from encode(self.body)

        yield '};'

    def __repr__(self):
        if self.body:
            body = ';'.join([str(x) for x in self.body]) + ';'
        else:
            body = ''

        return f'<{type(self).__name__} -> {self.name} : {self.inherits} {{ {body} }}>'

class A3Property:
    def __init__(self, name, value):
        self.name = name
        self.value = self._process_value(value)

    def __str__(self):
        return str(self.value)

    def encode_value(self, value):
        if isinstance(value, list):
            yield '{'
            yield ','.join([y for x in value for y in self.encode_value(x)])
            yield '}'
        elif isinstance(value, str):
            yield '"%s"' % re.sub(r'"', '""', value)
        else:
            yield str(value)

    def encode(self):
        yield self.name

        if isinstance(self.value, list):
            yield '[]'

        yield '='
        yield from self.encode_value(self.value)
        yield ';'

    def _process_value(self, value):
        #value = [x.value if hasattr(x, 'value') else x for x in value]
        #exit()

        if isinstance(value, list):
            return [self._process_value(x) for x in value if (isinstance(x, list) or not isinstance(x, str) or x.strip())]
        else:
            value = value.strip()

            if boolean := next((x for x in ('true', 'false') if x == value), None) is not None:
                return boolean

            if value and value[0] == '"' and value[-1] == '"':
                value = value[1:len(value) - 1]

            try:
                new_val = float(value)

                if new_val.is_integer():
                    new_val = int(new_val)

                return new_val
            except ValueError:
                return value

    def __repr__(self):
        return f'<{type(self).__name__} -> {self.name} = {repr(self.value)}>'
