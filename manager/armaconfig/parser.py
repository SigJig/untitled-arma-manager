
# TODO: Use trees instead of lists of tokens

import os
from pathlib import Path

from .scanner import Scanner, Token, TokenType
from .exceptions import UnexpectedType, UnexpectedValue
from .configtypes import A3Class, A3Property
from .stream import TokenStream, PreprocessedStream

class Parser:
    def __init__(self, unit):
        self._stream = PreprocessedStream(unit=unit)

    def _get_until(self, delim=';', token=None, **kwargs):
        seq = []
        token = token or self._stream.get(1, include_ws=True, **kwargs)

        while token.value not in delim:
            seq.append(token)

            token = self._stream.get(1, include_ws=True, **kwargs)

        return seq, token

    def _parse_value(self, sep=';', token=None):
        return ''.join([x.value for x in self._get_until(sep, token)[0]])

    def _parse_array(self):
        def __parse():
            seq = []
            seperators = ';,}'
            _, v = token = self._stream.get(1)

            if v == '{':
                seq.append(__parse())

                s = self._stream.get(1)
            else:
                val, s = self._get_until(seperators, token)
                seq.append(''.join([x.value for x in val]))

            if s.value in ',;':
                return seq + __parse()

            return seq

        self._stream.expect(values=['{'])
        
        val = __parse()

        self._stream.expect(values=[';'])

        return val

    def _parse_one(self, token=None):
        t, val = token = token or self._stream.get(1)

        if t == TokenType.IDENTIFIER:
            if val == 'class':
                _, name = self._stream.expect(types=[TokenType.IDENTIFIER])
                _, v = valuetoken = self._stream.expect(types=[TokenType.UNKNOWN])

                if v == ':':
                    inherits, opener = (x.value for x in self._stream.expect(types=[TokenType.IDENTIFIER, TokenType.UNKNOWN]))
                else:
                    inherits, opener = None, v

                if opener != '{': raise UnexpectedValue(expected=['{'], got=valuetoken)

                body = []
                token = self._stream.get(1)

                while not (token.type == TokenType.UNKNOWN and token.value == '}'):
                    body.append(next(self._parse_one(token)))
                    token = self._stream.get(1)

                self._stream.expect(values=[';'])

                yield A3Class(name, inherits, body)
            else:
                _, next_val = val_token = self._stream.expect(types=[TokenType.UNKNOWN])
                is_array = False

                if next_val == '[':
                    self._stream.expect(values=[']', '='])
                    
                    is_array = True
                elif next_val != '=':
                    raise UnexpectedValue(expected='=', got=val_token)

                yield A3Property(val, self._parse_array() if is_array else self._parse_value())
        elif t == TokenType.UNKNOWN and val == ';':
            return self._parse_one()
        else:
            raise UnexpectedType(expected=TokenType.IDENTIFIER, got=token)

    def parse(self):
        while True:
            try:
                yield from self._parse_one()
            except RuntimeError:
                return
