
import os, enum, collections

class TokenType(enum.Enum):
    UNKNOWN = 0
    STRING = 1
    PREPRO = 2
    IDENTIFIER = 3
    EOL = 4
    ARROW_STRING = 5

_Token = collections.namedtuple('Token', [
    'type',
    'value',
    'lineno',
    'colno',
    'unit'
])

class Token(_Token):
    def __iter__(self):
        return iter((self.type, self.value))

    def _asdict(self):
        return {f: getattr(self, f) for f in self._fields}

    @classmethod
    def from_token(cls, token, *args, **kwargs):
        td = token._asdict()
        td.update(**kwargs)

        return cls(*args, **td)


class Scanner:
    def __init__(self, unit):
        if isinstance(unit, (str, os.PathLike)):
            self._unit = unit

            with open(self._unit) as fp:
                self._lines = fp.readlines()
        else:
            self._stream = unit
            self._unit = self._stream.name
            self._lines = self._stream.readlines()

        self._lineno = 0
        self._cursor = 0

    @property
    def line(self):
        return self._get_line(self._lineno)
        
    def _get_line(self, lineno):
        try:
            return self._lines[lineno]
        except IndexError:
            return ''

    def _advance(self, length=1):
        self._cursor += length
        
        line_length = len(self.line)

        if self._cursor >= line_length:
            self._lineno += 1
            self._cursor = max(self._cursor - line_length, 0)
        elif self._cursor < 0:
            self._lineno = max(self._lineno - 1, 0)
            self._cursor = max(len(self.line) - abs(self._cursor), 0)

        if self._lineno >= len(self._lines):
            raise StopIteration

        return self

    def _peek(self, length=1):
        line_length = len(self.line)

        if self._cursor + length > line_length:
            remainder = self._cursor + length - line_length
            seq = ''

            for i in range(self._lineno + 1, len(self._lines)):
                line = self._get_line(i)

                if remainder >= len(line):
                    seq += line
                else:
                    seq += line[:remainder]
                    break
            else:
                #raise Unexpected(expected=[TokenType.UNKNOWN], got=TokenType.EOL)
                raise StopIteration

            return self.line[self._cursor:] + seq

        return self.line[self._cursor:self._cursor + length]

    def _get_raw(self, length=1):
        seq = self._peek(length)

        try:
            self._advance(length)
        except StopIteration:
            pass

        return seq

    def _find_delim(self, delim, advance=False):
        seq = ''
        length = len(delim)

        while self._peek(length) != delim:
            seq += self._get_raw(1)

        if advance:
            self._advance(length)

        return seq

    def _find_with_cb(self, callback, length=1, advance=False):
        seq = ''

        check = self._get_raw(length)

        while callback(check):
            seq += check
            check = self._get_raw(length)

        if not advance:
            self._advance(-length)


        return seq

    def _get_string(self):
        """
        This method assumes that the first " has been found
        """
        def callback(char):
            if char == '"':
                if self._peek() != '"':
                    return False

                self._advance(1)

            return True

        return self._find_with_cb(callback, length=1, advance=True)

    def is_identifier_char(self, char):
        return char.isalnum() or char == '_'

    def _iter_chars(self):
        while True:
            try:
                yield self._get_raw()
            except StopIteration:
                return

    def __iter__(self):
        return self

    def __next__(self):
        return self.scan()

    def _make_token(self, *args, **kwargs):
        kwargs.setdefault('lineno', self._lineno + 1)
        kwargs.setdefault('colno', self._cursor + 1)
        kwargs.setdefault('unit', self._unit)

        return Token(*args, **kwargs)

    def scan(self, simple=False):
        for char in self._iter_chars():
            if char == '/' and ((peek := self._peek()) in ['/', '*']):
                if peek == '/':
                    self._find_delim('\n', advance=True)
                else:
                    self._find_delim('*/', advance=True)
            elif char == '#' and not self.line[:self._cursor-1].strip():
                yield self._make_token(TokenType.PREPRO, '')
            elif char == '"':
                yield self._make_token(TokenType.STRING, '"{}"'.format(self._get_string()))
            elif char == '<':
                yield self._make_token(TokenType.ARROW_STRING, self._find_with_cb(lambda x: x != '>', advance=True))
            elif not simple and char == '_' or char.isalpha():
                yield self._make_token(TokenType.IDENTIFIER, char + self._find_with_cb(self.is_identifier_char))
            else:
                yield self._make_token(TokenType.UNKNOWN, char)
