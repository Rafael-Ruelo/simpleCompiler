from __future__ import annotations
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font, simpledialog


# ══════════════════════════════════════════════
#  COLOUR / STYLE CONSTANTS
# ══════════════════════════════════════════════

DARK_BG      = "#1e1e2e"
PANEL_BG     = "#181825"
TEXT_FG      = "#cdd6f4"
ACCENT       = "#89b4fa"
ACCENT2      = "#cba6f7"
GREEN        = "#a6e3a1"
RED          = "#f38ba8"
YELLOW       = "#f9e2af"
ORANGE       = "#fab387"
COMMENT_CLR  = "#6c7086"
KEYWORD_CLR  = "#cba6f7"
NUMBER_CLR   = "#fab387"
IDENT_CLR    = "#89dceb"
CURSOR_LINE  = "#313244"
SELECTION_BG = "#45475a"
BTN_BG       = "#313244"
BTN_ACTIVE   = "#45475a"

MONO_FONT    = ("Consolas", 12)
MONO_FONT_SM = ("Consolas", 10)
UI_FONT      = ("Segoe UI", 10)
UI_FONT_B    = ("Segoe UI", 10, "bold")

SAMPLE_CODE = """\
/* SimpleInt example program
   Computes sum and product of two inputs */

var a;
var b;
var sum;
var product;

input a;
input b;

sum = a + b;
product = a * b;

output sum;
output product;
"""


# ══════════════════════════════════════════════
#  SYNTAX HIGHLIGHTER
# ══════════════════════════════════════════════

class SyntaxHighlighter:

    KEYWORDS = {'var', 'input', 'output'}

    def __init__(self, text_widget: tk.Text):
        self.w = text_widget
        self._configure_tags()

    def _configure_tags(self):
        w = self.w
        w.tag_configure("keyword",  foreground=KEYWORD_CLR, font=(*MONO_FONT, "bold"))
        w.tag_configure("number",   foreground=NUMBER_CLR)
        w.tag_configure("comment",  foreground=COMMENT_CLR, font=(*MONO_FONT, "italic"))
        w.tag_configure("operator", foreground=ORANGE)
        w.tag_configure("ident",    foreground=IDENT_CLR)
        w.tag_configure("error_line", background="#3b1c1c")

    def rehighlight(self):
        w = self.w
        source = w.get("1.0", tk.END)

        # Remove all existing tags
        for tag in ("keyword", "number", "comment", "operator", "ident"):
            w.tag_remove(tag, "1.0", tk.END)

        lines = source.split('\n')
        in_comment = False
        for line_idx, line in enumerate(lines):
            line_no = line_idx + 1
            i       = 0
            while i < len(line):
                # Already inside a block comment
                if in_comment:
                    end = line.find('*/', i)
                    if end == -1:
                        # entire remaining line is comment
                        self._tag(w, "comment", line_no, i,
                                  line_no, len(line))
                        i = len(line)
                    else:
                        self._tag(w, "comment", line_no, i,
                                  line_no, end + 2)
                        i = end + 2
                        in_comment = False
                    continue

                # Start of block comment
                if i < len(line) - 1 and line[i] == '/' and line[i+1] == '*':
                    end = line.find('*/', i + 2)
                    if end == -1:
                        self._tag(w, "comment", line_no, i,
                                  line_no, len(line))
                        in_comment = True
                        i = len(line)
                    else:
                        self._tag(w, "comment", line_no, i,
                                  line_no, end + 2)
                        i = end + 2
                    continue

                ch = line[i]

                # Operator / punctuation
                if ch in '+-*/=;()':
                    self._tag(w, "operator", line_no, i, line_no, i+1)
                    i += 1
                    continue

                # Number
                if ch.isdigit():
                    j = i
                    while j < len(line) and line[j].isdigit():
                        j += 1
                    self._tag(w, "number", line_no, i, line_no, j)
                    i = j
                    continue

                # Keyword or identifier
                if ch.isalpha() or ch == '_':
                    j = i
                    while j < len(line) and (line[j].isalnum() or line[j] == '_'):
                        j += 1
                    word = line[i:j]
                    tag  = "keyword" if word in self.KEYWORDS else "ident"
                    self._tag(w, tag, line_no, i, line_no, j)
                    i = j
                    continue

                i += 1

    @staticmethod
    def _tag(w, tag, r1, c1, r2, c2):
        w.tag_add(tag, f"{r1}.{c1}", f"{r2}.{c2}")


#  LINE NUMBER GUTTER


class LineNumbers(tk.Canvas):
    """Canvas widget that renders line numbers alongside a Text widget."""

    def __init__(self, parent, text_widget: tk.Text, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget
        self.config(bg=PANEL_BG, highlightthickness=0, width=40)
        self._redraw()
        text_widget.bind("<KeyRelease>", lambda e: self._redraw())
        text_widget.bind("<MouseWheel>",  lambda e: self.after(10, self._redraw))
        text_widget.bind("<ButtonRelease>", lambda e: self._redraw())
        text_widget.bind("<<Change>>",    lambda e: self._redraw())
        text_widget.bind("<Configure>",   lambda e: self._redraw())

    def _redraw(self, _=None):
        self.delete("all")
        i    = self.text_widget.index("@0,0")
        w    = self.winfo_width() - 4
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y    = dline[1]
            line = str(i).split('.')[0]
            self.create_text(w, y + 2, anchor="ne", text=line,
                             fill=COMMENT_CLR, font=MONO_FONT_SM)
            i = self.text_widget.index(f"{i}+1line")
            if i == self.text_widget.index(f"{i}"):
                break


#  MAIN GUI CLASS


class CompilerGUI:

    def __init__(self, root: tk.Tk):
        self.root = root
        self._current_file: str | None = None

        # Threading primitives for async interpreter I/O
        self._input_queue:  queue.Queue[str] = queue.Queue()
        self._output_queue: queue.Queue      = queue.Queue()
        self._running       = False

        self._build_ui()
        self._apply_theme()
        self._editor.insert("1.0", SAMPLE_CODE)
        self._highlighter.rehighlight()
        self._update_status("Ready — press Run (▶) to execute.")

    # ── UI Construction ───────────────────────

    def _build_ui(self):
        root = self.root
        root.title("SimpleInt IDE")
        root.geometry("1100x800")
        root.minsize(800, 600)

        # ── Top toolbar ──
        self._build_toolbar()

        # ── Vertical PanedWindow ──
        pane = tk.PanedWindow(root, orient=tk.VERTICAL,
                              bg=DARK_BG, sashwidth=6,
                              sashrelief=tk.FLAT)
        pane.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # ── Top half: editor ──
        editor_frame = tk.Frame(pane, bg=DARK_BG)
        pane.add(editor_frame, minsize=200, stretch="always")
        self._build_editor(editor_frame)

        # ── Bottom half: notebook + console ──
        bottom_pane = tk.PanedWindow(pane, orient=tk.HORIZONTAL,
                                     bg=DARK_BG, sashwidth=6)
        pane.add(bottom_pane, minsize=150, stretch="always")
        self._build_notebook(bottom_pane)
        self._build_console(bottom_pane)

        # ── Status bar ──
        self._status_var = tk.StringVar(value="")
        status_bar = tk.Label(root, textvariable=self._status_var,
                              bg=PANEL_BG, fg=COMMENT_CLR,
                              font=UI_FONT, anchor="w", padx=8)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=PANEL_BG, height=44)
        tb.pack(side=tk.TOP, fill=tk.X)
        tb.pack_propagate(False)

        title = tk.Label(tb, text="  SimpleInt IDE",
                         bg=PANEL_BG, fg=ACCENT, font=("Segoe UI", 12, "bold"))
        title.pack(side=tk.LEFT, padx=(8, 16))

        btn_specs = [
            ("📂 Open",  self._open_file,  ACCENT),
            ("💾 Save",  self._save_file,  ACCENT),
            ("▶  Run",   self._run_code,   GREEN),
            ("⏹  Stop",  self._stop_code,  RED),
            ("🗑  Clear", self._clear_all,  ORANGE),
        ]
        self._run_btn  = None
        self._stop_btn = None

        for label, cmd, color in btn_specs:
            btn = tk.Button(
                tb, text=label, command=cmd,
                bg=BTN_BG, fg=color, activebackground=BTN_ACTIVE,
                activeforeground=color,
                relief=tk.FLAT, font=UI_FONT_B,
                padx=12, pady=6, cursor="hand2",
                bd=0, highlightthickness=0,
            )
            btn.pack(side=tk.LEFT, padx=3, pady=6)
            if "Run" in label:
                self._run_btn = btn
            if "Stop" in label:
                self._stop_btn = btn
                btn.config(state=tk.DISABLED, fg=COMMENT_CLR)

        # File name label (right side)
        self._file_label = tk.Label(tb, text="(unsaved)",
                                    bg=PANEL_BG, fg=COMMENT_CLR, font=UI_FONT)
        self._file_label.pack(side=tk.RIGHT, padx=12)

    def _build_editor(self, parent):
        label = tk.Label(parent, text=" Editor", bg=DARK_BG,
                         fg=ACCENT, font=UI_FONT_B, anchor="w")
        label.pack(fill=tk.X, padx=4)

        frame = tk.Frame(parent, bg=DARK_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # Line numbers
        self._editor = tk.Text(
            frame,
            bg=DARK_BG, fg=TEXT_FG,
            insertbackground=ACCENT,
            selectbackground=SELECTION_BG,
            selectforeground=TEXT_FG,
            font=MONO_FONT,
            wrap=tk.NONE,
            undo=True,
            relief=tk.FLAT,
            padx=8, pady=6,
            bd=0,
        )
        self._line_nos = LineNumbers(frame, self._editor, bg=PANEL_BG)
        self._line_nos.pack(side=tk.LEFT, fill=tk.Y)

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                            command=self._editor.yview)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL,
                            command=self._editor.xview)
        self._editor.configure(yscrollcommand=vsb.set,
                               xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Syntax highlighting on every keystroke
        self._highlighter = SyntaxHighlighter(self._editor)
        self._editor.bind("<KeyRelease>",
                          lambda e: self._highlighter.rehighlight())
        # Tab → spaces
        self._editor.bind("<Tab>", self._insert_spaces)

    def _build_notebook(self, parent):
        nb_frame = tk.Frame(parent, bg=DARK_BG)
        parent.add(nb_frame, minsize=300, stretch="always")

        style = ttk.Style()
        style.theme_use('default')
        style.configure('Custom.TNotebook',
                        background=DARK_BG, borderwidth=0)
        style.configure('Custom.TNotebook.Tab',
                        background=BTN_BG, foreground=TEXT_FG,
                        padding=[10, 4], font=UI_FONT)
        style.map('Custom.TNotebook.Tab',
                  background=[('selected', DARK_BG)],
                  foreground=[('selected', ACCENT)])

        self._nb = ttk.Notebook(nb_frame, style='Custom.TNotebook')
        self._nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._tokens_text  = self._add_text_tab("Tokens")
        self._ast_text     = self._add_text_tab("AST")
        self._symbols_text = self._add_text_tab("Symbols")

    def _add_text_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self._nb, bg=DARK_BG)
        self._nb.add(frame, text=f"  {title}  ")
        txt = scrolledtext.ScrolledText(
            frame,
            bg=PANEL_BG, fg=TEXT_FG,
            font=MONO_FONT_SM,
            relief=tk.FLAT, bd=0,
            padx=8, pady=6,
            state=tk.DISABLED,
            wrap=tk.NONE,
        )
        txt.pack(fill=tk.BOTH, expand=True)
        return txt

    def _build_console(self, parent):
        con_frame = tk.Frame(parent, bg=DARK_BG)
        parent.add(con_frame, minsize=250, stretch="always")

        label = tk.Label(con_frame, text=" Console",
                         bg=DARK_BG, fg=ACCENT, font=UI_FONT_B, anchor="w")
        label.pack(fill=tk.X, padx=4, pady=(4, 0))

        self._console = scrolledtext.ScrolledText(
            con_frame,
            bg=PANEL_BG, fg=TEXT_FG,
            font=MONO_FONT,
            relief=tk.FLAT, bd=0,
            padx=8, pady=6,
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self._console.pack(fill=tk.BOTH, expand=True, padx=4)

        # Configure console tags
        self._console.tag_configure("output",  foreground=GREEN)
        self._console.tag_configure("prompt",  foreground=YELLOW)
        self._console.tag_configure("error",   foreground=RED)
        self._console.tag_configure("warning", foreground=ORANGE)
        self._console.tag_configure("info",    foreground=ACCENT)
        self._console.tag_configure("dim",     foreground=COMMENT_CLR)

        # Input hint label
        self._input_hint = tk.Label(
            con_frame,
            text="",
            bg=DARK_BG, fg=YELLOW,
            font=UI_FONT_B, anchor="w"
        )
        self._input_hint.pack(fill=tk.X, padx=8, pady=(2, 4))

    # ── Theme ─────────────────────────────────

    def _apply_theme(self):
        style = ttk.Style()
        style.configure('Vertical.TScrollbar',
                        background=BTN_BG, troughcolor=PANEL_BG,
                        arrowcolor=COMMENT_CLR, borderwidth=0)
        style.configure('Horizontal.TScrollbar',
                        background=BTN_BG, troughcolor=PANEL_BG,
                        arrowcolor=COMMENT_CLR, borderwidth=0)

    # ── Helpers ───────────────────────────────

    def _insert_spaces(self, event):
        self._editor.insert(tk.INSERT, "    ")
        return "break"

    def _write_text(self, widget: tk.Text, text: str, tag: str = ""):
        widget.config(state=tk.NORMAL)
        if tag:
            widget.insert(tk.END, text, tag)
        else:
            widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)
        widget.see(tk.END)

    def _clear_widget(self, widget: tk.Text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.config(state=tk.DISABLED)

    def _write_console(self, text: str, tag: str = ""):
        self._write_text(self._console, text, tag)

    def _update_status(self, text: str):
        self._status_var.set(f"  {text}")

    # ── Toolbar actions ───────────────────────

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open SimpleInt Source",
            filetypes=[("SimpleInt files", "*.si"),
                       ("Text files", "*.txt"),
                       ("All files", "*.*")]
        )
        if not path:
            return
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", source)
        self._highlighter.rehighlight()
        self._current_file = path
        self._file_label.config(text=os.path.basename(path))
        self._update_status(f"Opened: {path}")

    def _save_file(self):
        if self._current_file:
            path = self._current_file
        else:
            path = filedialog.asksaveasfilename(
                title="Save SimpleInt Source",
                defaultextension=".si",
                filetypes=[("SimpleInt files", "*.si"),
                           ("Text files", "*.txt"),
                           ("All files", "*.*")]
            )
            if not path:
                return
        source = self._editor.get("1.0", tk.END)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(source)
        self._current_file = path
        self._file_label.config(text=os.path.basename(path))
        self._update_status(f"Saved: {path}")

    def _clear_all(self):
        self._clear_widget(self._console)
        self._clear_widget(self._tokens_text)
        self._clear_widget(self._ast_text)
        self._clear_widget(self._symbols_text)
        self._update_status("Cleared.")

    def _stop_code(self):
        # Signal any pending input request to abort
        self._input_queue.put("__STOP__")
        self._running = False

    # ── Run pipeline ──────────────────────────

    def _run_code(self):
        if self._running:
            return
        self._clear_all()
        source = self._editor.get("1.0", tk.END)
        if not source.strip():
            self._write_console("Nothing to run.\n", "warning")
            return

        # Disable run button, enable stop
        self._run_btn.config(state=tk.DISABLED, fg=COMMENT_CLR)
        self._stop_btn.config(state=tk.NORMAL, fg=RED)
        self._running = True

        self._write_console("─" * 50 + "\n", "dim")
        self._write_console("▶  Running SimpleInt program…\n", "info")
        self._write_console("─" * 50 + "\n", "dim")

        # Run on background thread
        t = threading.Thread(
            target=self._pipeline_thread,
            args=(source,),
            daemon=True
        )
        t.start()

        # Poll for output
        self._poll_output()

    def _pipeline_thread(self, source: str):
        import os
        sys.path.insert(0, os.path.dirname(__file__))

        from main import run_pipeline

        def gui_input(prompt: str) -> str:
            # Signal the GUI to show a popup dialog
            self._output_queue.put(('prompt', prompt))
            # Block here until the GUI puts a value back
            while True:
                val = self._input_queue.get()
                if val == "__STOP__":
                    raise InterruptedError("Execution stopped by user.")
                return val

        def gui_output(val):
            self._output_queue.put(('output', str(val)))

        result = run_pipeline(source,
                              input_func=gui_input,
                              output_func=gui_output)
        self._output_queue.put(('done', result))

    def _poll_output(self):
        try:
            while True:
                msg_type, payload = self._output_queue.get_nowait()

                if msg_type == 'output':
                    self._write_console(payload + "\n", "output")

                elif msg_type == 'prompt':
                    # Show input hint in console
                    self._write_console(payload + "\n", "prompt")
                    self._input_hint.config(
                        text="⌨  A popup dialog has opened — type your integer there."
                    )
                    # Show popup dialog on the main thread
                    self._show_input_dialog(payload)
                    return   # stop polling until dialog is answered

                elif msg_type == 'done':
                    self._input_hint.config(text="")
                    self._finish_run(payload)
                    return

        except queue.Empty:
            pass

        if self._running:
            self.root.after(50, self._poll_output)

    def _show_input_dialog(self, prompt: str):
        while True:
            val = simpledialog.askstring(
                title="Program Input",
                prompt=prompt,
                parent=self.root
            )
            # User closed / cancelled
            if val is None:
                self._input_queue.put("__STOP__")
                self._running = False
                self._run_btn.config(state=tk.NORMAL, fg=GREEN)
                self._stop_btn.config(state=tk.DISABLED, fg=COMMENT_CLR)
                self._write_console("⏹  Execution stopped by user.\n", "warning")
                self._input_hint.config(text="")
                return

            val = val.strip()
            try:
                int(val)   # validate it's an integer
                break
            except ValueError:
                messagebox.showerror(
                    "Invalid Input",
                    f"'{val}' is not a valid integer.\nPlease enter a whole number."
                )

        # Echo what was typed into the console
        self._write_console(f"  → You entered: {val}\n", "dim")
        self._input_hint.config(text="")
        self._input_queue.put(val)
        # Resume polling for more output
        self.root.after(50, self._poll_output)

    def _finish_run(self, result):
        """Called on the GUI thread when the interpreter finishes."""
        self._running = False
        self._run_btn.config(state=tk.NORMAL, fg=GREEN)
        self._stop_btn.config(state=tk.DISABLED, fg=COMMENT_CLR)

        # Show warnings
        for w in result.warnings:
            self._write_console(w + "\n", "warning")

        if result.success:
            self._write_console("─" * 50 + "\n", "dim")
            self._write_console("✔  Program finished successfully.\n", "info")
            self._update_status("✔ Execution complete.")
        else:
            self._write_console("─" * 50 + "\n", "dim")
            self._write_console(f"✘  {result.error}\n", "error")
            self._update_status(f"✘ {result.stage} error.")

        # Populate inspection tabs
        self._populate_tokens(result.tokens)
        self._populate_ast(result.ast)
        self._populate_symbols(result.symbol_table)

    # ── Inspection tab populators ─────────────

    def _populate_tokens(self, tokens):
        if not tokens:
            return
        self._clear_widget(self._tokens_text)
        header = f"{'#':<5} {'TYPE':<15} {'VALUE':<20} {'LINE':<6} {'COL'}\n"
        sep    = "─" * 55 + "\n"
        self._write_text(self._tokens_text, header)
        self._write_text(self._tokens_text, sep)
        for i, tok in enumerate(tokens):
            val = repr(tok.value) if tok.value is not None else "—"
            row = (f"{i:<5} {tok.type.name:<15} {val:<20} "
                   f"{tok.line:<6} {tok.column}\n")
            self._write_text(self._tokens_text, row)

    def _populate_ast(self, ast):
        if not ast:
            return
        from parser import ASTPrinter
        printer = ASTPrinter()
        text    = printer.print(ast)
        self._clear_widget(self._ast_text)
        self._write_text(self._ast_text, text + "\n")

    def _populate_symbols(self, table):
        if not table:
            return
        self._clear_widget(self._symbols_text)
        header = (f"{'NAME':<20} {'TYPE':<12} {'INITIALIZED':<14} "
                  f"{'DECLARED AT LINE'}\n")
        sep    = "─" * 60 + "\n"
        self._write_text(self._symbols_text, repr(table) + "\n\n")
        self._write_text(self._symbols_text, header)
        self._write_text(self._symbols_text, sep)
        for sym in table.all_symbols():
            row = (f"{sym.name:<20} {sym.type_name:<12} "
                   f"{str(sym.initialized):<14} {sym.line}\n")
            self._write_text(self._symbols_text, row)


#  STANDALONE LAUNCH


import os
import sys

if __name__ == '__main__':
    root = tk.Tk()
    app  = CompilerGUI(root)
    root.mainloop()
