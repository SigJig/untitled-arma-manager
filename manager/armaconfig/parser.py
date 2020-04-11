
import os
from pathlib import Path

from .scanner import Scanner, Token, TokenType
from .exceptions import UnexpectedType, UnexpectedValue
from .configtypes import A3Class, A3Property

class DefineStatement:
    def __init__(self, name, args, tokens):
        self.name = name
        self.args = args
        self.tokens = tokens
        
    def __call__(self):
        return iter(self.tokens)

    def __repr__(self):
        return str(list(self()))

class Parser:
    def __init__(self, unit):
        self._scanners = []
        self._make_scanner(unit)

        self._buf = []
        self._proc_buf = []

        self.defined = {}
        self.links = []

    @property
    def scanner(self):
        return self._scanners[-1]

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

        self._proc_buf.extend(list(self._preprocess(token)))

        return self._get_preprocessed(**getter_args)

    def _get_raw(self, include_ws=False):
        token = (self._buf and self._buf.pop(0)) or self.next_token()

        if not include_ws and token.type == TokenType.UNKNOWN and token.value.isspace():
            return self._get_raw(include_ws)
        
        return token

    def _peek(self, length=1, **kwargs):
        for _ in range(length):
            self._buf.append(self.next_token(**kwargs))

        if len(self._buf) == 1:
            return self._buf[0]

        return self._buf

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

    def _preprocess(self, token, **getter_args):
        t, val = token
        #print(token)

        if t != TokenType.PREPRO:
            if t == TokenType.IDENTIFIER and val in self.defined:
                func = self.defined[val]
                args = []

                if self._peek().value == '(':
                    self._get(1)

                    nxt = self._get(1)

                    """ while not (nxt.type == TokenType.UNKNOWN and nxt.value == ')'):
                        if nxt.type != TokenType.IDENTIFIER:
                            raise Unexpected(expected=[TokenType.IDENTIFIER, TokenType.UNKNOWN], got=nxt.type)

                        args.append(nxt.value)

                        nxt = self._get(1)
                        if nxt.type == TokenType.UNKNOWN and nxt.value == ',':
                            nxt = self._get(1) """
                

                yield from (func(*args))
            else:
                yield token
        else:
            _, command = cmd_token = self._get(1, preprocessed=False)

            if command == 'include':
                t, path = path_token = self._get(1, preprocessed=False)

                if t == TokenType.STRING:
                    path = path[1:-1]
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

                self.defined[name] = DefineStatement(name, args, tokens)
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
            else:
                yield token
                yield cmd_token

    def _if_def(self, is_defined, is_else=False):
        token = self._get(1, preprocessed=False)

        while True:
            if token.type == TokenType.PREPRO:
                t, cmd = peeked = self._peek(1, preprocessed=True)

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
        

    def _parse_value(self, is_array=False):
        seperators = ';,}' if is_array else ';'

        seq = ''

        _, v = self._get(1)

        if v == '{' and is_array:
            seq = self._parse_value(is_array)

            _, v = self._get(1, expect_typ=[TokenType.UNKNOWN])
        else:
            while v not in seperators:
                seq += v
                _, v = self._get(1, include_ws=True)

            if not is_array: return seq

        seq = [seq]

        if v in ';,':
            return seq + self._parse_value(is_array)

        return seq

    def _parse_array(self):
        self._expect_sequence(val='{')

        val = self._parse_value(True)
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
