from __future__ import annotations
from parser import (
    ASTNode, Program, VarDecl, AssignStmt, InputStmt, OutputStmt,
    BinOp, UnaryOp, IntegerLiteral, Identifier
)

#  EXCEPTIONS


class SemanticError(Exception):
    def __init__(self, message: str, line: int | None = None,
                 column: int | None = None):
        self.message = message
        self.line    = line
        self.column  = column
        if line is not None:
            loc = f"Line {line}, Col {column}"
            super().__init__(f"[Semantic Error] {loc}: {message}")
        else:
            super().__init__(f"[Semantic Error] {message}")


class SemanticWarning:
    def __init__(self, message: str, line: int | None = None,
                 column: int | None = None):
        self.message = message
        self.line    = line
        self.column  = column

    def __str__(self):
        if self.line is not None:
            return f"[Semantic Warning] Line {self.line}, Col {self.column}: {self.message}"
        return f"[Semantic Warning] {self.message}"

#  SYMBOL / SYMBOL TABLE

class Symbol:
    def __init__(self, name: str, type_name: str = 'INTEGER',
                 line: int | None = None, column: int | None = None):
        self.name        = name
        self.type_name   = type_name
        self.initialized = False       # set to True on first assignment/input
        self.line        = line
        self.column      = column

    def __repr__(self):
        init_str = "initialized" if self.initialized else "uninitialized"
        return f"<Symbol name={self.name!r} type={self.type_name} {init_str}>"


class SymbolTable:

    def __init__(self, scope_name: str, scope_level: int,
                 enclosing_scope: 'SymbolTable | None' = None):
        self._symbols:      dict[str, Symbol] = {}
        self.scope_name     = scope_name
        self.scope_level    = scope_level
        self.enclosing_scope = enclosing_scope

    def insert(self, symbol: Symbol) -> None:
        self._symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol | None:
        sym = self._symbols.get(name)
        if sym is not None:
            return sym
        if self.enclosing_scope is not None:
            return self.enclosing_scope.lookup(name)
        return None

    def lookup_current(self, name: str) -> Symbol | None:
        return self._symbols.get(name)

    def all_symbols(self) -> list[Symbol]:
        return list(self._symbols.values())

    def __repr__(self) -> str:
        sep = "-" * 50
        rows = "\n".join(
            f"  {sym.name:<20} type={sym.type_name:<10} "
            f"init={sym.initialized}  declared@line={sym.line}"
            for sym in self._symbols.values()
        )
        return (f"\n{sep}\n"
                f" SYMBOL TABLE : {self.scope_name!r}  (level {self.scope_level})\n"
                f"{sep}\n"
                + (rows if rows else "  (empty)") + "\n")


#  SEMANTIC ANALYZER

class SemanticAnalyzer:
    def __init__(self):
        self.current_scope: SymbolTable | None = None
        self.warnings:      list[SemanticWarning] = []

    # ── Error / warning helpers ───────────────

    def _error(self, message: str, line: int | None = None,
               column: int | None = None) -> None:
        raise SemanticError(message, line, column)

    def _warn(self, message: str, line: int | None = None,
              column: int | None = None) -> None:
        self.warnings.append(SemanticWarning(message, line, column))

    # ── Visitor dispatch ──────────────────────

    def _visit(self, node: ASTNode):
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode):
        raise NotImplementedError(
            f"SemanticAnalyzer has no visitor for {type(node).__name__}"
        )

    # ── Public entry point ────────────────────

    def analyze(self, tree: ASTNode) -> SymbolTable:
        self.current_scope = SymbolTable(
            scope_name='global',
            scope_level=1,
            enclosing_scope=None
        )
        self._visit(tree)
        return self.current_scope

    # ── Visitor implementations ───────────────

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            self._visit(stmt)

    def visit_VarDecl(self, node: VarDecl) -> None:
        if self.current_scope.lookup_current(node.identifier):
            self._error(
                f"Variable '{node.identifier}' is already declared in this scope.",
                node.line, node.column
            )
        symbol = Symbol(
            name      = node.identifier,
            type_name = 'INTEGER',
            line      = node.line,
            column    = node.column
        )
        self.current_scope.insert(symbol)

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        symbol = self.current_scope.lookup(node.identifier)
        if symbol is None:
            self._error(
                f"Variable '{node.identifier}' used before declaration.",
                node.line, node.column
            )
        # Check right-hand side for undeclared references
        self._visit(node.expression)
        # Mark variable as initialized after we know the RHS is valid
        symbol.initialized = True

    def visit_InputStmt(self, node: InputStmt) -> None:
        symbol = self.current_scope.lookup(node.identifier)
        if symbol is None:
            self._error(
                f"Variable '{node.identifier}' used before declaration.",
                node.line, node.column
            )
        symbol.initialized = True

    def visit_OutputStmt(self, node: OutputStmt) -> None:
        self._visit(node.expression)

    def visit_BinOp(self, node: BinOp) -> str:
        left_type  = self._visit(node.left)
        right_type = self._visit(node.right)
        # Type check: both must be INTEGER (they always will be in SimpleInt,
        # but we check explicitly to support future type extensions).
        if left_type != 'INTEGER' or right_type != 'INTEGER':
            self._error(
                f"Type mismatch in binary operation '{node.op.value}': "
                f"expected INTEGER op INTEGER, got {left_type} op {right_type}."
            )
        return 'INTEGER'

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand_type = self._visit(node.operand)
        if operand_type != 'INTEGER':
            self._error(
                f"Type mismatch in unary '{node.op.value}': "
                f"expected INTEGER, got {operand_type}."
            )
        return 'INTEGER'

    def visit_IntegerLiteral(self, node: IntegerLiteral) -> str:
        return 'INTEGER'

    def visit_Identifier(self, node: Identifier) -> str:
        symbol = self.current_scope.lookup(node.name)
        if symbol is None:
            self._error(
                f"Variable '{node.name}' used before declaration.",
                node.line, node.column
            )
        if not symbol.initialized:
            self._warn(
                f"Variable '{node.name}' may be read before being assigned a value.",
                node.line, node.column
            )
        return symbol.type_name   # 'INTEGER'
