from __future__ import annotations
from typing import Callable

from lexer import TokenType
from stack import CallStack, ActivationRecord
from parser import (
    ASTNode, Program, VarDecl, AssignStmt, InputStmt, OutputStmt,
    BinOp, UnaryOp, IntegerLiteral, Identifier
)


#  RUNTIME EXCEPTION


class RuntimeError(Exception):
    def __init__(self, message: str, line: int | None = None,
                 column: int | None = None):
        self.message = message
        self.line    = line
        self.column  = column
        if line is not None:
            super().__init__(
                f"[Runtime Error] Line {line}, Col {column}: {message}"
            )
        else:
            super().__init__(f"[Runtime Error] {message}")


#  INTERPRETER


class Interpreter:

    def __init__(
        self,
        input_func:  Callable[[str], str] | None = None,
        output_func: Callable[[object], None] | None = None,
    ):
        self.call_stack  = CallStack()
        self._input_fn   = input_func  or self._default_input
        self._output_fn  = output_func or print

    # ── I/O defaults (terminal) ───────────────

    @staticmethod
    def _default_input(prompt: str = "") -> str:
        return input(prompt)

    # ── Error helper ──────────────────────────

    def _error(self, message: str, line: int | None = None,
               column: int | None = None) -> None:
        raise RuntimeError(message, line, column)

    # ── Visitor dispatch ──────────────────────

    def _visit(self, node: ASTNode):
        method_name = f"visit_{type(node).__name__}"
        visitor     = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode):
        raise NotImplementedError(
            f"Interpreter has no visitor for {type(node).__name__}"
        )

    # ── Public entry point ────────────────────

    def interpret(self, tree: ASTNode) -> None:
        ar = ActivationRecord(name='PROGRAM', level=1)
        self.call_stack.push(ar)
        try:
            self._visit(tree)
        finally:
            self.call_stack.pop()

    # ── Statement visitors ────────────────────

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            self._visit(stmt)

    def visit_VarDecl(self, node: VarDecl) -> None:
        ar = self.call_stack.peek()
        ar[node.identifier] = None   # declared, not yet assigned

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        ar    = self.call_stack.peek()
        value = self._visit(node.expression)
        ar[node.identifier] = value

    def visit_InputStmt(self, node: InputStmt) -> None:
        ar = self.call_stack.peek()
        while True:
            try:
                raw   = self._input_fn(f"Enter value for '{node.identifier}': ")
                value = int(raw.strip())
                break
            except ValueError:
                # Re-prompt; the GUI callback can raise to abort cleanly.
                self._output_fn(
                    f"  ⚠  Invalid input '{raw}' — please enter an integer."
                )
            except (EOFError, KeyboardInterrupt):
                self._error("Input was interrupted or no more data available.")
        ar[node.identifier] = value

    def visit_OutputStmt(self, node: OutputStmt) -> None:
        value = self._visit(node.expression)
        self._output_fn(value)

    # ── Expression visitors ───────────────────

    def visit_BinOp(self, node: BinOp) -> int:
        left  = self._visit(node.left)
        right = self._visit(node.right)

        op = node.op.type

        if op == TokenType.PLUS:
            return left + right

        if op == TokenType.MINUS:
            return left - right

        if op == TokenType.MULTIPLY:
            return left * right

        if op == TokenType.DIVIDE:
            if right == 0:
                self._error(
                    "Division by zero.",
                    node.op.line, node.op.column
                )
            # Use integer (truncating) division — matches language spec.
            return int(left / right)

        self._error(
            f"Unknown binary operator '{node.op.value}'.",
            node.op.line, node.op.column
        )

    def visit_UnaryOp(self, node: UnaryOp) -> int:
        operand = self._visit(node.operand)
        if node.op.type == TokenType.MINUS:
            return -operand
        self._error(f"Unknown unary operator '{node.op.value}'.")

    def visit_IntegerLiteral(self, node: IntegerLiteral) -> int:
        return node.value

    def visit_Identifier(self, node: Identifier) -> int:
        ar  = self.call_stack.peek()
        val = ar.get(node.name)

        if val is None:
            # Declared but never assigned — caught at semantic analysis
            # level as a warning; guard here as a runtime safety net.
            if node.name in ar:
                self._error(
                    f"Variable '{node.name}' is declared but has no value yet.",
                    node.line, node.column
                )
            else:
                self._error(
                    f"Undeclared variable '{node.name}'.",
                    node.line, node.column
                )

        return val

    # ── Introspection helpers ─────────────────

    def get_current_frame(self) -> ActivationRecord | None:
        return self.call_stack.peek() if not self.call_stack.is_empty() else None

    def dump_stack(self) -> str:
        return repr(self.call_stack)
