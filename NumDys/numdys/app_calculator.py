from gi.repository import Gtk

from .safe_eval import evaluate, format_result, ExpressionError


class CalculatorApp(Gtk.Box):
    """Calculatrice scientifique : historique des calculs + pavé de touches."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state
        self.expression = ""

        # --- Historique ------------------------------------------------
        self.history_store = Gtk.ListBox()
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_min_content_height(140)
        self.scroll.add(self.history_store)
        self.pack_start(self.scroll, True, True, 0)

        # --- Champ de saisie --------------------------------------------
        self.display = Gtk.Entry()
        self.display.set_name("display")
        self.display.set_alignment(1.0)
        self.display.connect("activate", self.on_equals)
        self.pack_start(self.display, False, False, 0)

        # --- Pavé de touches ----------------------------------------------
        grid = Gtk.Grid(row_spacing=2, column_spacing=2, column_homogeneous=True)
        self.pack_start(grid, False, False, 0)

        rows = [
            [("sin", "function"), ("cos", "function"), ("tan", "function"), ("(", "function"), (")", "function")],
            [("ln", "function"), ("log", "function"), ("√", "function"), ("^", "operator"), ("π", "function")],
            [("7", "number"), ("8", "number"), ("9", "number"), ("÷", "operator"), ("C", "function")],
            [("4", "number"), ("5", "number"), ("6", "number"), ("×", "operator"), ("⌫", "function")],
            [("1", "number"), ("2", "number"), ("3", "number"), ("-", "operator"), ("Ans", "function")],
            [("0", "number"), (",", "number"), ("e", "function"), ("+", "operator"), ("=", "equals")],
        ]

        for row_index, row in enumerate(rows):
            for col_index, (label, style_class) in enumerate(row):
                btn = Gtk.Button(label=label)
                btn.get_style_context().add_class(style_class)
                btn.connect("clicked", self.on_key, label)
                grid.attach(btn, col_index, row_index, 1, 1)

    # ------------------------------------------------------------------
    def on_key(self, _widget, label):
        if label == "C":
            self.display.set_text("")
        elif label == "⌫":
            text = self.display.get_text()
            self.display.set_text(text[:-1])
        elif label == "=":
            self.on_equals(None)
        elif label == "Ans":
            self._insert(format_result(self.state.last_answer))
        else:
            self._insert(label)

    def _insert(self, text):
        pos = self.display.get_position()
        current = self.display.get_text()
        self.display.set_text(current[:pos] + text + current[pos:])
        self.display.set_position(pos + len(text))
        self.display.grab_focus()

    def on_equals(self, _widget):
        expr = self.display.get_text()
        if not expr.strip():
            return
        try:
            value = evaluate(expr, degree_mode=self.state.degree_mode)
            result_text = format_result(value)
            self.state.last_answer = value
            self._add_history(expr, result_text, error=False)
            self.display.set_text(result_text)
        except ExpressionError as exc:
            self._add_history(expr, str(exc), error=True)

    def _add_history(self, expr, result_text, error):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        expr_label = Gtk.Label(label=expr)
        expr_label.set_halign(Gtk.Align.END)
        expr_label.get_style_context().add_class("numdys-label")
        result_label = Gtk.Label(label=result_text)
        result_label.set_halign(Gtk.Align.END)
        result_label.get_style_context().add_class(
            "numdys-error" if error else "numdys-result"
        )
        box.pack_start(expr_label, False, False, 0)
        box.pack_start(result_label, False, False, 0)
        row.add(box)
        self.history_store.add(row)
        self.history_store.show_all()

        # Défile automatiquement vers le bas
        adj = self.scroll.get_vadjustment()
        if adj is not None:
            adj.set_value(adj.get_upper())
