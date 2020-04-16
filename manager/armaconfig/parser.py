
import os
from pathlib import Path

from .scanner import Scanner, Token, TokenType
from .exceptions import UnexpectedType, UnexpectedValue
from .configtypes import A3Class, A3Property

class TokenIterator:
    def __init__(self, tokens):
        self._tokens = tokens
        self._buf = []

    def __iter__(self):
        return self

    def __next__(self):
        return self.get(1)

    def get(self, length, expect_type=None, expect_value=None, *args, **kwargs):
        buf_len =  len(self._buf)
        seq = self._buf[:length]

        del self._buf[:length]

        if length > buf_len:
            for _ in range(length - buf_len):
                try:
                    seq.append(self._next_token(*args, **kwargs))
                except StopIteration:
                    break

        if len(seq) == 1:
            return seq[0]

        return seq

    def discard(self, length):
        try:
            for _ in range(length): self._next_token()
        except StopIteration:
            pass

    def peek(self, length, *args, **kwargs):
        buf_len = len(self._buf)

        if length >= buf_len:
            for _ in range(length - buf_len):
                try:
                    self._buf.append(self._next_token(*args, **kwargs))
                except StopIteration:
                    break

        seq = self._buf[:length]

        if len(seq) == 1:
            return seq[0]

        return seq

    def _next_token(self):
        if self._buf: return self._buf.pop(0)

        return next(self._tokens)

class DefineStatement:
    def __init__(self, parser, name, args, tokens):
        self.parser = parser
        self.name = name
        self.args = args
        self.tokens = TokenIterator(tokens)

    def __call__(self, *args):
        expect, got = len(self.args), len(args)

        if expect != got:
            raise TypeError(f'Expected {expect} positional arguments, got {got}')
        
        for index, token in enumerate(self.tokens):
            type_, value = token

            if type_ == TokenType.IDENTIFIER:
                new_token = Token.from_token(token, value=token.value)

                while True:
                    if all(
                            (x.type == TokenType.UNKNOWN and x.value == '#')
                            for x in self.tokens.peek(2)
                        ):
                        
                        self.tokens.discard(2)

                        new_token.value += self.tokens.get(1, expect_type=[TokenType.IDENTIFIER])
                    else:
                        break

                yield new_token
            elif type_ == TokenType.UNKNOWN and value == '#':
                if self.tokens.peek(1)[0].value == '#':
                    raise UnexpectedValue('Not # lmao', '#')
                
                nxt = self.tokens.get(1, expect_type=[TokenType.IDENTIFIER])
                arg_names = [x.value for x in self.args]

                if not nxt.value in arg_names:
                    raise UnexpectedValue(arg_names, nxt.value)

                arg = args[arg_names.index(nxt.value)]

                yield Token.from_token(arg, type=TokenType.STRING, value=str(arg.value))

    def __repr__(self):
        return f'{type(self).__name__}: {self.name}({",".join(self.args)})'

class Parser:
    def __init__(self, unit):
        self._scanners = []
        self._make_scanner(unit)

        self.tokens = TokenIterator(self._iter_tokens)

        self._buf = []
        self._proc_buf = []

        self.defined = {}
        self.links = []

    @property
    def scanner(self):
        return self._scanners[-1]

    def _iter_tokens(self):
        while True:
            try:
                yield from self.scanner.scan()
            except (StopIteration, IndexError):
                if len(self._scanners) <= 0:
                    raise StopIteration

    def _make_scanner(self, unit):
        self._scanners.append(Scanner(unit))

        return self.scanner

    def next_token(self, preprocessed=False):
        try:
            if preprocessed and self._proc_buf:
                return self._proc_buf.pop(0)

            return next(self.scanner.scan())
        except StopIteration:
            if len(self._scanners) <= 1:
                raise StopIteration

            self._scanners.pop()
        
            return self.next_token()

    def _get_preprocessed(self, **getter_args):
        if self._proc_buf:
            return self._proc_buf.pop(0)

        token = self._get_raw(**getter_args)

        if token.type == TokenType.IDENTIFIER:
            try:
                g = self._process_defined(token)
            except UnexpectedValue:
                return token
            else:
                self._proc_buf.extend(g)
        else:
            self._proc_buf.extend(self._preprocess(token))

        return self._get_preprocessed(**getter_args)

    def _get_raw(self, include_ws=False, buf=True):
        token = (buf and self._buf and self._buf.pop(0)) or self.next_token()

        if not include_ws and token.type == TokenType.UNKNOWN and token.value.isspace():
            return self._get_raw(include_ws)
        
        return token

    def _get(self, length=1, expect_typ=None, expect_val=None, preprocessed=True, **kwargs):
        getter = self._get_preprocessed if preprocessed else self._get_raw

        seq = [getter(**kwargs) for _ in range(length)]

        if expect_typ is not None:
            for i in range(len(expect_typ)):
                if seq[i].type != expect_typ[i]:
                    raise UnexpectedType(expected=expect_typ[i], got=seq[i])

        if expect_val is not None:
            for i in range(len(expect_val)):
                if seq[i].value != expect_val[i]:
                    raise UnexpectedValue(expected=expect_val[i], got=seq[i])

        if length == 1:
            return seq[0]

        return seq

    def _expect_sequence(self, typ=None, val=None, **kwargs):
        assert None in (typ, val), '_expect_sequence: either typ or val has to be None'
        
        if typ is not None:
            for i in range(len(typ)):
                t, _ = token = self._get(**kwargs)

                if t != typ[i]:
                    raise UnexpectedType(expected=typ[i], got=token)

        elif val is not None:
            for i in range(len(val)):
                _, v = token = self._get(**kwargs)

                if v != val[i]:
                    raise UnexpectedValue(expected=val[i], got=token)
        else:
            assert False, 'ok fuckhead'

    def _process_defined(self, token):
        t, v = token

        if t != TokenType.IDENTIFIER:
            raise UnexpectedType(TokenType.IDENTIFIER, token)
        elif v not in self.defined:
            raise UnexpectedValue(self.defined.keys(), token)

        args = []
        func = self.defined[v]

        if self._peek().value == '(':
            self._get(1) # Discard the first '('

            nxt, delim = self._get_until(',)')

            while delim.value != ')':
                args.append(nxt)

                nxt, delim = self._get_until(',)')
            args.append(nxt)

        print(args)

        return func(*args)

    def _preprocess(self, token, **getter_args):
        t, val = token

        if t != TokenType.PREPRO:
            yield token

            return

        _, command = cmd_token = self._get(1, preprocessed=False)

        if command == 'include':
            t, path = path_token = self._get(1, preprocessed=False)

            if t == TokenType.STRING:
                path = path[1:-1] # Strip quotes
            elif t != TokenType.ARROW_STRING:
                raise UnexpectedType([TokenType.STRING, TokenType.ARROW_STRING], path_token)
                
            split = path.split('\\')
            joined_path = Path.cwd()

            if '.' in split: raise Exception('Dots not allowed maybe idek')

            self._make_scanner(joined_path.joinpath(*split))

        elif command == 'define':
            _, name = self._get(1, preprocessed=False, expect_typ=[TokenType.IDENTIFIER])
            
            nxt = self._get(1, preprocessed=False, include_ws=True)
            args = []

            if nxt.value == '(':
                while nxt.value != ')':
                    argument, comma = self._get(2, preprocessed=False, expect_typ=[TokenType.IDENTIFIER, TokenType.UNKNOWN])

                    if comma.value not in '),':
                        raise UnexpectedValue(expected=[')', ','], got=comma)
                    
                    args.append(argument.value)
                    nxt = comma

                nxt = self._get(1, preprocessed=False, include_ws=True)

            tokens = []
            while True:
                if nxt.value == '\\':
                    self._expect_sequence(val='\n')
                elif nxt.value == '\n':
                    break
                else:
                    tokens.append(nxt)

                nxt = self._get(1, preprocessed=False, include_ws=True)

            self.defined[name] = DefineStatement(self, name, args, tokens)
        elif command in ['ifdef', 'ifndef']:
            _, identifier = self._get(1, preprocessed=False, expect_typ=[TokenType.IDENTIFIER])

            is_defined = identifier in self.defined

            if command == 'ifdef':
                gen = self._if_def(is_defined)
            else:
                gen = self._if_def(not is_defined)

            for token in gen:
                yield from self._preprocess(token)

        elif command == 'undef':
            _, identifier = self._get(1, preprocessed=False, expect_typ=[TokenType.IDENTIFIER])

            if identifier in self.defined:
                del self.defined[identifier]

    def _if_def(self, is_defined, is_else=False):
        token = self._get(1, preprocessed=False)

        while True:
            if token.type == TokenType.PREPRO:
                t, cmd = peeked = self._peek(1)

                if t == TokenType.IDENTIFIER and cmd in ('else', 'endif'):
                    self._get(1, preprocessed=False)
                    
                    if cmd == 'else':
                        if not is_else:
                            yield from self._if_def(not is_defined, is_else=True)
                        else:
                            raise UnexpectedValue(expected=['endif'], got=peeked)

                    return

            if is_defined:
                yield token

            token = self._get(1, preprocessed=False)

    def _get_until(self, delim=';', token=None, **kwargs):
        seq = []
        token = token or self._get(1, include_ws=True, **kwargs)

        while token.value not in delim:
            seq.append(token)

            token = self._get(1, include_ws=True, **kwargs)

        return seq, token

    def _parse_value(self, sep=';', token=None):
        return ''.join([x.value for x in self._get_until(sep, token)[0]])

    def _parse_array(self):
        def __parse():
            seq = []
            seperators = ';,}'
            _, v = token = self._get(1)

            if v == '{':
                seq.append(__parse())

                s = self._get(1)
            else:
                val, s = self._get_until(seperators, token)
                seq.append(''.join([x.value for x in val]))

            if s.value in ',;':
                return seq + __parse()

            return seq

        self._expect_sequence(val='{')
        
        val = __parse()

        self._expect_sequence(val=';')

        return val

    def _parse_one(self, token=None):
        t, val = token = token or self._get(1)

        if t == TokenType.IDENTIFIER:
            if val == 'class':
                _, name = self._get(1, expect_typ=[TokenType.IDENTIFIER])
                _, v = valuetoken = self._get(1, expect_typ=[TokenType.UNKNOWN])

                if v == ':':
                    inherits, opener = (x.value for x in self._get(2, expect_typ=[TokenType.IDENTIFIER, TokenType.UNKNOWN]))
                else:
                    inherits, opener = None, v

                if opener != '{': raise UnexpectedValue(expected=['{'], got=valuetoken)

                body = []
                token = self._get(1)

                while not (token.type == TokenType.UNKNOWN and token.value == '}'):
                    body.append(next(self._parse_one(token)))
                    token = self._get(1)

                self._expect_sequence(val=';')

                yield A3Class(name, inherits, body)
            else:
                _, next_val = val_token = self._get(1, expect_typ=[TokenType.UNKNOWN])
                is_array = False

                if next_val == '[':
                    self._expect_sequence(val=[']', '='])
                    
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
