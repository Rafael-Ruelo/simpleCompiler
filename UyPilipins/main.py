from __future__ import annotations
import sys
import os

#  PIPELINE RESULT

class CompileResult:

    def __init__(self):
        self.tokens       = None
        self.ast          = None
        self.symbol_table = None
        self.output_lines: list[str] = []
        self.warnings:     list[str] = []
        self.error:        str | None = None
        self.stage:        str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    def __repr__(self):
        status = "OK" if self.success else f"ERROR ({self.stage})"
        return (f"CompileResult(status={status}, "
                f"output_lines={self.output_lines}, "
                f"warnings={self.warnings})")


#  PIPELINE FUNCTION

def run_pipeline(
    source:       str,
    input_func=   None,
    output_func=  None,
) -> CompileResult:
    from lexer             import Lexer,             LexerError
    from parser            import Parser,            ParseError
    from semantic_analyzer import SemanticAnalyzer,  SemanticError
    from interpreter       import Interpreter,       RuntimeError

    result    = CompileResult()
    collected: list[str] = []

    # ── Output collector: capture + forward ──
    def _collect_output(val):
        s = str(val)
        collected.append(s)
        if output_func:
            output_func(val)

    # ── Stage 1: Lexical Analysis ─────────────
    try:
        lexer         = Lexer(source)
        result.tokens = lexer.tokenize()
    except LexerError as e:
        result.error = str(e)
        result.stage = "Lexer"
        return result

    # ── Stage 2: Parsing ──────────────────────
    try:
        parser    = Parser(result.tokens)
        result.ast = parser.parse()
    except ParseError as e:
        result.error = str(e)
        result.stage = "Parser"
        return result

    # ── Stage 3: Semantic Analysis ────────────
    try:
        analyzer           = SemanticAnalyzer()
        result.symbol_table = analyzer.analyze(result.ast)
        result.warnings    = [str(w) for w in analyzer.warnings]
    except SemanticError as e:
        result.error = str(e)
        result.stage = "Semantic Analyzer"
        return result

    # ── Stage 4: Interpretation ───────────────
    try:
        interp = Interpreter(
            input_func  = input_func,
            output_func = _collect_output,
        )
        interp.interpret(result.ast)
    except RuntimeError as e:
        result.error        = str(e)
        result.stage        = "Interpreter"
        result.output_lines = collected   # preserve partial output
        return result
    except Exception as e:
        result.error        = f"[Unexpected Error] {e}"
        result.stage        = "Interpreter"
        result.output_lines = collected
        return result

    result.output_lines = collected
    return result

#  FILE RUNNER

def run_file(path: str) -> int:
    if not os.path.isfile(path):
        print(f"[Error] File not found: {path!r}", file=sys.stderr)
        return 1

    with open(path, 'r', encoding='utf-8') as fh:
        source = fh.read()

    result = run_pipeline(source, output_func=print)

    if result.warnings:
        for w in result.warnings:
            print(w, file=sys.stderr)

    if not result.success:
        print(result.error, file=sys.stderr)
        return 1

    return 0

#  REPL

def run_repl() -> None:
    banner = (
        "\n"
        "╔══════════════════════════════════════════════╗\n"
        "║   Uy Pilipins                                ║\n"
        "║   Type statements; blank line to execute.    ║\n"
        "║   Type 'exit' or 'quit' to leave.            ║\n"
        "╚══════════════════════════════════════════════╝\n"
    )
    print(banner)

    while True:
        lines: list[str] = []
        try:
            while True:
                prompt = ">>> " if not lines else "... "
                line   = input(prompt)
                if line.lower() in ('exit', 'quit') and not lines:
                    print("Goodbye.")
                    return
                if line == "" and lines:
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        source = "\n".join(lines)
        if not source.strip():
            continue

        result = run_pipeline(source, output_func=print)

        for w in result.warnings:
            print(w)

        if not result.success:
            print(result.error)
        elif not result.output_lines:
            print("(no output)")

#  ENTRY POINT

def main() -> int:
    args = sys.argv[1:]

    # ── REPL mode ─────────────────────────────
    if args and args[0] in ('--repl', '-r'):
        run_repl()
        return 0

    # ── File mode ─────────────────────────────
    if args:
        return run_file(args[0])

    # ── GUI mode (default) ────────────────────
    try:
        import tkinter as tk
        from gui import CompilerGUI
        root = tk.Tk()
        app  = CompilerGUI(root)
        root.mainloop()
        return 0
    except ImportError as e:
        print(f"[Error] Could not launch GUI: {e}", file=sys.stderr)
        print("Usage: python main.py [source_file.si | --repl]",
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
