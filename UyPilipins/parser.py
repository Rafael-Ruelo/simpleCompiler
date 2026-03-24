from __future__ import annotations
from lexer import Token, TokenType

#  AST NODE HIERARCHY


class ASTNode:
    pass


# ── Structural nodes ──────────────────────────

class Program(ASTNode):
    def __init__(self, statements: list[ASTNode]):
        self.statements = statements

    def __repr__(self):
        return f"Program(statements=[{len(self.statements)} stmts])"


# ── Statement nodes ───────────────────────────

class VarDecl(ASTNode):
    def __init__(self, identifier: str, line: int, column: int):
        self.identifier = identifier
        self.line       = line
        self.column     = column

    def __repr__(self):
        return f"VarDecl(name={self.identifier!r}, line={self.line})"


class AssignStmt(ASTNode):
    def __init__(self, identifier: str, expression: ASTNode,
                 line: int, column: int):
        self.identifier = identifier
        self.expression = expression
        self.line       = line
        self.column     = column

    def __repr__(self):
        return (f"AssignStmt(target={self.identifier!r}, "
                f"expr={self.expression!r})")


class InputStmt(ASTNode):
    def __init__(self, identifier: str, line: int, column: int):
        self.identifier = identifier
        self.line       = line
        self.column     = column

    def __repr__(self):
        return f"InputStmt(var={self.identifier!r}, line={self.line})"


class OutputStmt(ASTNode):
    def __init__(self, expression: ASTNode, line: int, column: int):
        self.expression = expression
        self.line       = line
        self.column     = column

    def __repr__(self):
        return f"OutputStmt(expr={self.expression!r})"


# ── Expression nodes ──────────────────────────

class BinOp(ASTNode):
    def __init__(self, left: ASTNode, op: Token, right: ASTNode):
        self.left  = left
        self.op    = op
        self.right = right

    def __repr__(self):
        return f"BinOp({self.left!r} {self.op.value} {self.right!r})"


class UnaryOp(ASTNode):
    def __init__(self, op: Token, operand: ASTNode):
        self.op      = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.op.value}{self.operand!r})"


class IntegerLiteral(ASTNode):
    def __init__(self, token: Token):
        self.token = token
        self.value = token.value        # already an int from Lexer

    def __repr__(self):
        return f"IntegerLiteral({self.value})"


class Identifier(ASTNode):
    def __init__(self, token: Token):
        self.token  = token
        self.name   = token.value
        self.line   = token.line
        self.column = token.column

    def __repr__(self):
        return f"Identifier({self.name!r})"

#  PARSE ERROR

class ParseError(Exception):

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line    = line
        self.column  = column
        super().__init__(
            f"[Parse Error] Line {line}, Col {column}: {message}"
        )

#  RECURSIVE-DESCENT PARSER

class Parser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0            # index of current lookahead token

    # ── Internal helpers ──────────────────────

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _error(self, msg: str) -> None:
        tok = self._current()
        raise ParseError(msg, tok.line, tok.column)

    def _eat(self, expected_type: TokenType) -> Token:
        tok = self._current()
        if tok.type != expected_type:
            self._error(
                f"Expected '{expected_type.name}', "
                f"got '{tok.type.name}' (value={tok.value!r})"
            )
        self.pos += 1
        return tok

    # ── Grammar productions ───────────────────

    def parse(self) -> Program:
        node = self._parse_program()
        self._eat(TokenType.EOF)
        return node

    def _parse_program(self) -> Program:
        statements: list[ASTNode] = []
        while self._current().type != TokenType.EOF:
            statements.append(self._parse_statement())
        return Program(statements)

    def _parse_statement(self) -> ASTNode:
        tt = self._current().type

        if tt == TokenType.VAR:
            return self._parse_var_decl()
        elif tt == TokenType.INPUT:
            return self._parse_input_stmt()
        elif tt == TokenType.OUTPUT:
            return self._parse_output_stmt()
        elif tt == TokenType.IDENTIFIER:
            return self._parse_assign_stmt()
        else:
            tok = self._current()
            self._error(
                f"Unexpected token '{tok.value}' — "
                f"expected 'var', 'input', 'output', or an identifier"
            )

    def _parse_var_decl(self) -> VarDecl:
        """var_decl = 'var' IDENTIFIER ';'"""
        kw  = self._eat(TokenType.VAR)
        id_ = self._eat(TokenType.IDENTIFIER)
        self._eat(TokenType.SEMICOLON)
        return VarDecl(id_.value, kw.line, kw.column)

    def _parse_assign_stmt(self) -> AssignStmt:
        """assign_stmt = IDENTIFIER '=' expression ';'"""
        id_tok = self._eat(TokenType.IDENTIFIER)
        self._eat(TokenType.ASSIGN)
        expr = self._parse_expression()
        self._eat(TokenType.SEMICOLON)
        return AssignStmt(id_tok.value, expr, id_tok.line, id_tok.column)

    def _parse_input_stmt(self) -> InputStmt:
        """input_stmt = 'input' IDENTIFIER ';'"""
        kw  = self._eat(TokenType.INPUT)
        id_ = self._eat(TokenType.IDENTIFIER)
        self._eat(TokenType.SEMICOLON)
        return InputStmt(id_.value, kw.line, kw.column)

    def _parse_output_stmt(self) -> OutputStmt:
        """output_stmt = 'output' expression ';'"""
        kw   = self._eat(TokenType.OUTPUT)
        expr = self._parse_expression()
        self._eat(TokenType.SEMICOLON)
        return OutputStmt(expr, kw.line, kw.column)

    def _parse_expression(self) -> ASTNode:
        node = self._parse_term()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op   = self._current()
            self.pos += 1
            right = self._parse_term()
            node  = BinOp(node, op, right)
        return node

    def _parse_term(self) -> ASTNode:
        node = self._parse_factor()
        while self._current().type in (TokenType.MULTIPLY, TokenType.DIVIDE):
            op   = self._current()
            self.pos += 1
            right = self._parse_factor()
            node  = BinOp(node, op, right)
        return node

    def _parse_factor(self) -> ASTNode:
        tok = self._current()
        tt  = tok.type

        if tt == TokenType.LPAREN:
            self._eat(TokenType.LPAREN)
            node = self._parse_expression()
            self._eat(TokenType.RPAREN)
            return node

        elif tt == TokenType.MINUS:
            op = self._current()
            self.pos += 1
            operand = self._parse_factor()
            return UnaryOp(op, operand)

        elif tt == TokenType.INTEGER:
            self.pos += 1
            return IntegerLiteral(tok)

        elif tt == TokenType.IDENTIFIER:
            self.pos += 1
            return Identifier(tok)

        else:
            self._error(
                f"Expected a value (number or variable) or '(', "
                f"got '{tok.value}'"
            )

#  AST PRETTY-PRINTER  (utility)

class ASTPrinter:

    def print(self, node: ASTNode, indent: int = 0) -> str:
        method = getattr(self, f'_print_{type(node).__name__}',
                         self._print_generic)
        return method(node, indent)

    def _pad(self, indent: int) -> str:
        return "  " * indent

    def _print_generic(self, node: ASTNode, indent: int) -> str:
        return self._pad(indent) + repr(node)

    def _print_Program(self, node: Program, indent: int) -> str:
        lines = [self._pad(indent) + "Program"]
        for stmt in node.statements:
            lines.append(self.print(stmt, indent + 1))
        return "\n".join(lines)

    def _print_VarDecl(self, node: VarDecl, indent: int) -> str:
        return self._pad(indent) + f"VarDecl  → {node.identifier!r}"

    def _print_AssignStmt(self, node: AssignStmt, indent: int) -> str:
        lines = [self._pad(indent) + f"Assign  → {node.identifier!r}"]
        lines.append(self.print(node.expression, indent + 1))
        return "\n".join(lines)

    def _print_InputStmt(self, node: InputStmt, indent: int) -> str:
        return self._pad(indent) + f"Input   → {node.identifier!r}"

    def _print_OutputStmt(self, node: OutputStmt, indent: int) -> str:
        lines = [self._pad(indent) + "Output"]
        lines.append(self.print(node.expression, indent + 1))
        return "\n".join(lines)

    def _print_BinOp(self, node: BinOp, indent: int) -> str:
        lines = [self._pad(indent) + f"BinOp({node.op.value!r})"]
        lines.append(self.print(node.left,  indent + 1))
        lines.append(self.print(node.right, indent + 1))
        return "\n".join(lines)

    def _print_UnaryOp(self, node: UnaryOp, indent: int) -> str:
        lines = [self._pad(indent) + f"UnaryOp({node.op.value!r})"]
        lines.append(self.print(node.operand, indent + 1))
        return "\n".join(lines)

    def _print_IntegerLiteral(self, node: IntegerLiteral, indent: int) -> str:
        return self._pad(indent) + f"Integer({node.value})"

    def _print_Identifier(self, node: Identifier, indent: int) -> str:
        return self._pad(indent) + f"Var({node.name!r})"
