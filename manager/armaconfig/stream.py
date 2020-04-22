
import os, functools
from pathlib import Path
from typing import Union

from .scanner import Scanner, TokenType, Token, TokenCollection
from .exceptions import Unexpected, UnexpectedType, UnexpectedValue

def arr_or_only(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs) -> Union[list, TokenType]:
        retrn = f(*args, **kwargs)

        if isinstance(retrn, (tuple, list)) and len(retrn) == 1:
            return retrn[0]

        return retrn
    return wrapper

def process_identifier(preprocessor, stream, identifier):
    if identifier.value in preprocessor.defined:
        f = preprocessor.defined[identifier.value]
        args = []
        nxt = stream.peek(1)

        if nxt.type == TokenType.UNKNOWN and nxt.value == '(':
            stream.discard(1)

            cur = TokenCollection()
            while True:
                nxt = stream.get(1)

                if nxt.type == TokenType.UNKNOWN:
                    if nxt.value in '),':
                        args.append(cur)
                        cur = TokenCollection()

                        if nxt.value == ')':
                            break
                        else:
                            continue
                    else:
                        cur.append(nxt)
                elif nxt.type == TokenType.IDENTIFIER:
                    cur.extend(process_identifier(preprocessor, stream, nxt))
                else:
                    cur.append(nxt)

        yield from f(*args)
    else:
        yield identifier

class DefineStatement:
    def __init__(self, preprocessor, name, args, tokens):
        self.name = name
        self.args = args
        self.tokens = TokenStream(tokens, iter_include_ws=True)
        self.preprocessor = preprocessor

    def __call__(self, *args):
        def resolve_identifier(identifier):
            names = self.args

            if identifier.value in names:
                yield args[names.index(identifier.value)]
            else:
                yield from process_identifier(self.preprocessor, self.tokens, identifier)

        expect, got = len(self.args), len(args)

        if expect != got:
            raise TypeError(f'Expected {expect} positional arguments, got {got}')
        
        for index, token in enumerate(self.tokens):
            type_, value = token

            if type_ == TokenType.IDENTIFIER:
                collection = TokenCollection(resolve_identifier(token))

                while True:
                    try:
                        t, v = self.tokens.peek(1, include_ws=True)
                    except StopIteration:
                        break

                    if t == TokenType.DOUBLE_HASH:
                        self.tokens.discard(1)

                        identifier = resolve_identifier(self.tokens.get(1, include_ws=True, expect_type=[TokenType.IDENTIFIER]))

                        collection.extend(identifier)
                    else:
                        break

                yield collection
            elif type_ == TokenType.UNKNOWN and value == '#':
                collection = TokenCollection(self.__call__(*args), type=TokenType.STRING)

                yield collection
            else:
                yield token

    def __repr__(self):
        return f'{type(self).__name__}: {self.name}({",".join(self.args)})'

class TokenStream:
    def __init__(self, tokens=None, unit=None, iter_include_ws=False):
        assert None in (tokens, unit) and any(x is not None for x in (tokens, unit)), (
            'Tokenstream: Exactly one of `tokens`, `unit` must be non-None'
        )

        self._tokens = tokens
        self._buf = []
        self._scanners = []
        self._unit = unit
        self._iter_include_ws = iter_include_ws

        if self._tokens is not None:
            self._iterator = iter(self._tokens)
        else:
            self.add_scanner(self._unit)
            self._iterator = self._iter_from_scanner()

    def __iter__(self):
        return self

    def __next__(self):
        return self.get(1, include_ws=self._iter_include_ws)

    @property
    def scanner(self):
        return self._scanners[-1]

    @property
    def path(self):
        if self._unit is None:
            raise KeyError('path')

        if isinstance(self._unit, (str, os.PathLike)):
            p = Path(self._unit)
        else:
            p = Path(self._unit.name)

        return p.resolve()

    def add_scanner(self, unit):
        self._scanners.append(Scanner(unit))

        return self.scanner

    @arr_or_only
    def get(self, length, expect_type=None, expect_value=None, *args, **kwargs):
        buf_len =  len(self._buf)
        seq = self._buf[:length]

        del self._buf[:length]

        if length > buf_len:
            for _ in range(length - buf_len):
                seq.append(self._next_token(*args, **kwargs))

        return seq

    def discard(self, length):
        try:
            for _ in range(length): self._next_token()
        except StopIteration:
            pass

    @arr_or_only
    def peek(self, length, *args, **kwargs):
        buf_len = len(self._buf)

        tmp_buf = []

        if length >= buf_len:
            for _ in range(length - buf_len):
                tmp_buf.append(self._next_token(*args, **kwargs))

        self._buf.extend(tmp_buf)

        return self._buf[:length]

    @arr_or_only
    def expect(self, values=None, types=None, **getter_args):
        assert None in (values, types) and any(x is not None for x in (values, types)), (
            'Invalid arguments: Exactly one of `values`, `types` must be non-None'
        )

        chk = values or types
        
        if chk == values:
            k = 'value'
            error = UnexpectedValue
        else:
            k = 'type'
            error = UnexpectedType

        seq = []
        for i in chk:
            token = self.get(1, **getter_args)

            if getattr(token, k) != i:
                raise error(i, token)

            seq.append(token)

        return seq

    def _iter_from_scanner(self):
        while True:
            try:
                yield from self.scanner.scan()
            except (StopIteration, IndexError):
                if len(self._scanners) <= 1:
                    raise StopIteration

                self._scanners.pop()

    def _next_token(self, include_ws=False):
        token = (self._buf and self._buf.pop(0)) or next(self._iterator)

        if not include_ws and token.type == TokenType.UNKNOWN and token.value.isspace():
            return self._next_token(include_ws)

        return token

class PreprocessedStream(TokenStream):
    CLS_IGNORE = (
        'scanner', 'path', 'add_scanner', '_iter_from_scanner'
    )

    def __init__(self, *args, **kwargs):
        self.defined = {}

        self.tokens = TokenStream(*args, **kwargs)
        self._iterator = self.iter_preprocessed()
        self._buf = []

    def iter_preprocessed(self):
        while True:
            try:
                if not self._buf:
                    self._buf.extend(self._preprocess(self.tokens.get(1)))

                    if not self._buf:
                        continue

                yield self._buf.pop(0)
            except StopIteration:
                return

    def _preprocess(self, token):
        if token.type == TokenType.PREPRO:
            _, command = cmdtoken = self.tokens.expect(types=[TokenType.IDENTIFIER])

            if command == 'define':
                _, name = self.tokens.expect(types=[TokenType.IDENTIFIER])
                args = []

                if self.tokens.peek(1).value == '(':
                    self.tokens.discard(1)

                    while True:
                        t, v = nxt = self.tokens.get(1)

                        if t == TokenType.IDENTIFIER:
                            args.append(v)

                            nxt = self.tokens.peek(1)

                            if nxt.type == TokenType.UNKNOWN:
                                if nxt.value == ',':
                                    self.tokens.discard(1)
                                    continue
                                elif nxt.value == ')': continue
                                else: raise UnexpectedValue([',', ')'], nxt)
                            else:
                                raise UnexpectedType([TokenType.UNKNOWN], nxt)

                        elif t == TokenType.UNKNOWN:
                            if v != ')':
                                raise UnexpectedValue(')', nxt)

                            break
                        else:
                            raise UnexpectedType([TokenType.IDENTIFIER, TokenType.UNKNOWN], nxt)

                tokens = TokenCollection()
                while True:
                    nxt = self.tokens.get(1, include_ws=True)

                    if nxt.value == '\\':
                        self.tokens.expect(values=['\n'])
                    elif nxt.value == '\n':
                        break
                    elif nxt.type != TokenType.UNKNOWN or nxt.value != ' ':
                        # Ignore spaces, but include tabs
                        tokens.append(nxt)

                self.defined[name] = DefineStatement(self, name, args, tokens)
            elif command == 'include':
                t, path = path_token = self.tokens.get(1)

                if t == TokenType.STRING:
                    if all(x == '"' for x in (path[0], path[-1])):
                        path = path[1:-1]
                elif t != TokenType.ARROW_STRING:
                    raise UnexpectedType([TokenType.STRING, TokenType.ARROW_STRING], path_token)

                self.tokens.add_scanner(self.path.joinpath(path))

            elif command in ('ifdef', 'ifndef'):
                def ifdef(is_defined, is_else=False):
                    while True:
                        t, _ = token = self.tokens.get(1)

                        if t == TokenType.PREPRO:
                            peek = self.tokens.peek(1)

                            if peek.type == TokenType.IDENTIFIER and peek.value in ('endif', 'else'):
                                self.tokens.discard(1)

                                if peek.value == 'else':
                                    if not is_else:
                                        yield from ifdef(not is_defined, is_else=True)
                                        return
                                    else:
                                        raise UnexpectedValue(['endif'], peek)
                                else:
                                    return
                            else:
                                yield from self._preprocess(token)
                        else:
                            yield from self._preprocess(token)

                macro = self.tokens.get(1, expect_type=[TokenType.IDENTIFIER])
                is_defined = macro.value in self.defined

                if command == 'ifdef':
                    yield from ifdef(is_defined)
                else:
                    yield from ifdef(not is_defined)
            elif command in 'undef':
                _, name = self.tokens.expect(types=[TokenType.IDENTIFIER])

                if name in self.defined:
                    del self.defined[name]
                
        elif token.type == TokenType.IDENTIFIER:
            yield from process_identifier(self, self.tokens, token)
        else:
            yield token

