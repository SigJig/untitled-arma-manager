
from typing import Union, Sequence, Any

from .scanner import Token, TokenType

def format_expected(e, got, token):
    return 'Expected %s, got %s (%s)' % (e, got, token)

class Unexpected: pass

class UnexpectedType(TypeError, Unexpected):
    def __init__(self, expected: Union[TokenType, Sequence[TokenType]], got: Token):
        if isinstance(expected, (list, tuple)):
            expected = '<%s>' % (' | '.join([str(x) for x in expected]))
        else:
            expected = str(expected)

        message = format_expected(expected, str(got.type), repr(got))

        super().__init__(message)

class UnexpectedValue(ValueError, Unexpected):
    def __init__(self, expected: Any, got: Token):
        message = format_expected(repr(expected), repr(got.value), repr(got))

        super().__init__(message)
