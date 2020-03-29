
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

class Parser:
    def __init__(self, stream, buf_len=1024):
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

    def _parse_value(self, char=None):
        return self._get_while(is_identifier, char=char)

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
                body.append(self._parse_value(char=next_char))

            next_char = self._get(1)

            if next_char not in ('}', ','):
                raise InvalidCharacterException(expected=['}', ','], got=next_char)

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

            return self._parse_class()
        elif is_identifier(char):
            return self._parse_variable(char)
        
        raise InvalidCharacterException(expected=['class', 'variable'], got=char + self._get(1))

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