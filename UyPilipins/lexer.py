from enum import Enum, auto


#  Token Types


class TokenType(Enum):
    # ── Keywords ──────────────────────────────
    VAR       = auto()   # 'var'    — variable declaration
    INPUT     = auto()   # 'input'  — read from console
    OUTPUT    = auto()   # 'output' — write to console

    # ── Literals ──────────────────────────────
    INTEGER   = auto()   # e.g. 42, 0, 1000
    IDENTIFIER= auto()   # e.g. x, myVar, _count1

    # ── Arithmetic Operators ──────────────────
    PLUS      = auto()   # +
    MINUS     = auto()   # -
    MULTIPLY  = auto()   # *
    DIVIDE    = auto()   # /

    # ── Assignment ────────────────────────────
    ASSIGN    = auto()   # =

    # ── Punctuation ───────────────────────────
    SEMICOLON = auto()   # ;
    LPAREN    = auto()   # (
    RPAREN    = auto()   # )

    # ── Sentinel ──────────────────────────────
    EOF       = auto()   # End-of-file marker


#  Token Data Class

class Token:
    __slots__ = ('type', 'value', 'line', 'column')

    def __init__(self, type_: TokenType, value, line: int, column: int):
        self.type   = type_
        self.value  = value
        self.line   = line
        self.column = column

    def __repr__(self):
        return (f"Token(type={self.type.name:<12} "
                f"value={self.value!r:<15} "
                f"line={self.line}, col={self.column})")


#  Lexer Error


class LexerError(Exception):

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line    = line
        self.column  = column
        super().__init__(
            f"[Lexer Error] Line {line}, Col {column}: {message}"
        )


#  Lexer


class Lexer:
    # Map reserved words to their token type
    KEYWORDS: dict[str, TokenType] = {
        'lalagyan':    TokenType.VAR,
        'ilagay':  TokenType.INPUT,
        'kinalabasan': TokenType.OUTPUT,
    }

    # Map single characters to token types
    SINGLE_CHAR: dict[str, TokenType] = {
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.MULTIPLY,
        '/': TokenType.DIVIDE,
        '=': TokenType.ASSIGN,
        ';': TokenType.SEMICOLON,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
    }

    def __init__(self, source: str):
        self.source  = source
        self.pos     = 0          # current read position in source
        self.line    = 1          # current line number (1-based)
        self.column  = 1          # current column number (1-based)

    # ── Private helpers ──────────────────────

    def _current(self) -> str | None:
        return self.source[self.pos] if self.pos < len(self.source) else None

    def _peek(self) -> str | None:
        nxt = self.pos + 1
        return self.source[nxt] if nxt < len(self.source) else None

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line  += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _error(self, msg: str):
        raise LexerError(msg, self.line, self.column)

    # ── Scanning helpers ─────────────────────

    def _skip_whitespace(self):
        while self._current() in (' ', '\t', '\r', '\n'):
            self._advance()

    def _skip_block_comment(self):
        self._advance()   # consume '/'
        self._advance()   # consume '*'
        while self._current() is not None:
            if self._current() == '*' and self._peek() == '/':
                self._advance()   # consume '*'
                self._advance()   # consume '/'
                return
            self._advance()
        self._error("Unterminated block comment — missing closing '*/'")

    def _read_integer(self) -> Token:
        start_line = self.line
        start_col  = self.column
        digits     = []
        while self._current() is not None and self._current().isdigit():
            digits.append(self._advance())
        return Token(TokenType.INTEGER, int(''.join(digits)), start_line, start_col)

    def _read_identifier_or_keyword(self) -> Token:
        start_line = self.line
        start_col  = self.column
        chars      = []
        while (self._current() is not None and
               (self._current().isalnum() or self._current() == '_')):
            chars.append(self._advance())
        lexeme = ''.join(chars)
        ttype  = self.KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        return Token(ttype, lexeme, start_line, start_col)

    # ── Public interface ──────────────────────

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while True:
            self._skip_whitespace()
            ch = self._current()

            if ch is None:
                # End of source — emit EOF sentinel
                tokens.append(Token(TokenType.EOF, None, self.line, self.column))
                break

            # ── Block comment ─────────────────
            if ch == '/' and self._peek() == '*':
                self._skip_block_comment()
                continue

            # ── Integer literal ───────────────
            if ch.isdigit():
                tokens.append(self._read_integer())
                continue

            # ── Identifier or keyword ─────────
            if ch.isalpha() or ch == '_':
                tokens.append(self._read_identifier_or_keyword())
                continue

            # ── Single-character tokens ───────
            if ch in self.SINGLE_CHAR:
                line, col = self.line, self.column
                self._advance()
                tokens.append(Token(self.SINGLE_CHAR[ch], ch, line, col))
                continue

            # ── Unknown character — error ─────
            self._error(f"Unexpected character '{ch}' (ASCII {ord(ch)})")

        return tokens
