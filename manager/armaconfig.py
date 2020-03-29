
import functools

from pathlib import Path
from typing import Any

class InvalidCharacterException(Exception):
    def __init__(self, expected: list, got: str):
        super().__init__(f'Invalid character encountered: Expected ({", ".join(expected)}), got "{got}"')

def is_identifier(string):
    if not (string[0] == '_' or string[0].isalpha()):
        return False

    return all(x.isalnum() or x == '_' for x in string)

class A3Class:
    def __init__(self, name, inherits, body):
        self.name = name
        self.inherits = inherits
        self.body = body

    def __repr__(self):
        return f'<{type(self).__name__} -> {self.name} : {self.inherits} {{ {self.body} }}>'

class A3Property:
    def __init__(self, name, value):
        self.name = name
        self.value = self._process_value(value)

    def _process_value(self, value):
        if isinstance(value, list):
            return [self._process_value(x) for x in value]
        else:
            value = value.strip()

            if value and value[0] == '"':
                if value[-1] != '"':
                    raise Exception('Fuck you ' + value)

                value = value[1:len(value) - 1]

            try:
                new_val = float(value)

                if new_val.is_integer():
                    new_val = int(new_val)

                return new_val
            except ValueError:
                return value

    def __repr__(self):
        return f'<{type(self).__name__} -> {self.name} = {self.value}>'

class Parser:
    def __init__(self, stream, buf_len=2048):
        self._stream = stream
        self._buf_len = buf_len
        self._cursor = 0
        
        self._update_chunk()

    def _move_cursor(self, length):
        self._cursor += length

        return self

    def _update_chunk(self, buf_len=None):
        if buf_len is None:
            buf_len = self._buf_len

        chunk = self._stream.read(buf_len)
        self._cursor = max(self._cursor - buf_len, 0)
        self._chunk = chunk
        
        return chunk

    def _get_while(self, cb, char=None, *args, **kwargs):
        seq = ''
        char = char or self._get(*args, **kwargs)

        while cb(seq + char):
            seq += char
            char = self._get(*args, **kwargs)
        
        # Move the cursor back so the invalid character can be read again later
        self._move_cursor(-1)

        return seq

    def _get(self, length=1, include_ws=False):
        chunk = self._peek(length)

        if not include_ws and chunk[0].isspace():
            self._cursor += 1

            return self._get(length)

        self._move_cursor(length)

        return chunk

    def _peek(self, length=1):
        if self._cursor + length > self._buf_len:
            self._update_chunk(self._cursor + length - self._buf_len)

        return self._chunk[self._cursor:self._cursor + length]

    def _parse_class_body(self):
        next_char = self._get(1)
        body = []

        while next_char != '}':
            body.append(self._parse_one(next_char))
            next_char = self._get(1)

        next_char = self._get(1)
        if next_char != ';':
            raise InvalidCharacterException(expected=[';'], got=next_char)

        return body

    def _parse_class(self):
        data = {
            'name': self._get_while(is_identifier),
            'inherits': None,
            'body': []
        }

        if not data['name']:
            raise Exception(f'Unnamed class encountered')

        next_char = self._get(1)

        if next_char == ':':
            data['inherits'] = self._get_while(is_identifier)
            next_char = self._get(1)
        
        if next_char == '{':
            data['body'] = self._parse_class_body()
        else:
            raise InvalidCharacterException(expected=[':', '{'], got=next_char)

        return data

    def _parse_string(self, char=None):
        next_char = char or self._get(1, include_ws=True)
        seq = ''

        while True:
            if next_char == '"':
                if self._peek(1) == '"':
                    seq += self._get(1, include_ws=True)
                else:
                    return seq + next_char
            else:
                seq += next_char

            next_char = self._get(1, include_ws=True)

    def _parse_value(self, is_array=False, char=None):
        special_chars = [';', ',', '}'] if is_array else [';']

        next_char = char or self._get(1, include_ws=True)
        seq = ''

        while next_char not in special_chars:
            if next_char == '"':
                seq += '"' + self._parse_string()
            else:
                seq += next_char

            next_char = self._get(1, include_ws=True)

        self._move_cursor(-1)

        return seq

    def _parse_array(self, char=None):
        next_char = char or self._get(1)

        if next_char != '{':
            raise InvalidCharacterException(expected=['{'], got=next_char)

        body = []

        while next_char != '}':
            next_char = self._get(1)

            if next_char == '{':
                body.append(self._parse_array(char=next_char))
            else:
                body.append(self._parse_value(is_array=True, char=next_char))

            next_char = self._get(1)

            if next_char not in ('}', ',', ';'):
                raise InvalidCharacterException(expected=['}', ',', ';'], got=next_char)

        return body

    def _parse_variable(self, char=None):
        name = self._get_while(is_identifier, char=char)

        if not name:
            raise Exception(f'Shit needs a name bitch')

        next_char = self._get(1)
        is_array = False

        if next_char == '[':
            closing = self._get(1)
            next_char = self._get(1)

            if closing != ']':
                raise InvalidCharacterException(expected=[']'], got=closing)

            is_array = True
        
        if next_char != '=':
            raise InvalidCharacterException(expected=['='], got=next_char)

        value = self._parse_array() if is_array else self._parse_value()

        next_char = self._get(1)

        if next_char != ';':
            raise InvalidCharacterException(expected=[';'], got=next_char)

        return {
            'name': name,
            'value': value
        }

    def _parse_one(self, char=None):
        char = char or self._get(1)

        if char == 'c' and self._peek(4) == 'lass':
            self._move_cursor(4)

            return A3Class(**self._parse_class())
        elif is_identifier(char):
            return A3Property(**self._parse_variable(char))
        
        raise InvalidCharacterException(expected=['class', 'variable'], got=char)

    def parse(self):
        try:
            yield self._parse_one()

            self.parse()
        except:
            raise

if __name__ == '__main__':
    with open(Path.cwd().joinpath('config.githide.cfg')) as fp:
        p = Parser(fp)

        for i in p.parse():
            print(i)