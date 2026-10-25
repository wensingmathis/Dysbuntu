"""Écran calculatrice et historique borné en mémoire."""
from gi.repository import GLib, Gtk, Pango

from .safe_eval import ExpressionError, MAX_EXPRESSION_LENGTH, evaluate, format_result

HISTORY_LIMIT = 100


class CalculatorApp(Gtk.Box):
    """Calculatrice scientifique à saisie manuelle ou par touches."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state

        self.history_store = Gtk.ListBox()
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(140)
        scroll.add(self.history_store)
        self.scroll = scroll
        self.pack_start(scroll, True, True, 0)

        self.display = Gtk.Entry()
        self.display.set_name("display")
        self.display.set_alignment(1.0)
        self.display.set_max_length(MAX_EXPRESSION_LENGTH)
        self.display.set_placeholder_text("Ex. : sin(30) + 2^3")
        self.display.connect("activate", self.on_equals)
        self.pack_start(self.display, False, False, 0)

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
            for column_index, (text, css_class) in enumerate(row):
                button = Gtk.Button(label=text)
                button.get_style_context().add_class(css_class)
                button.connect("clicked", self.on_key, text)
                grid.attach(button, column_index, row_index, 1, 1)

    def _selected_range(self) -> tuple[int, int]:
        """Compatible avec les variantes d'API PyGObject GtkEditable."""
        result = self.display.get_selection_bounds()
        if result and len(result) == 2:
            return result
        if result and len(result) == 3 and result[0]:
            return result[1], result[2]
        cursor = self.display.get_position()
        return cursor, cursor

    def on_key(self, _widget, label: str) -> None:
        if label == "C":
            self.display.set_text("")
        elif label == "⌫":
            start, end = self._selected_range()
            if start != end:
                self.display.delete_text(start, end)
            else:
                pos = self.display.get_position()
                if pos > 0:
                    self.display.delete_text(pos - 1, pos)
        elif label == "=":
            self.on_equals(None)
        elif label == "Ans":
            self._insert(f"({format_result(self.state.last_answer)})")
        else:
            token = {"sin": "sin(", "cos": "cos(", "tan": "tan(",
                     "ln": "ln(", "log": "log(", "√": "sqrt(", "π": "pi"}.get(label, label)
            self._insert(token)

    def _insert(self, text: str) -> None:
        start, end = self._selected_range()
        current = self.display.get_text()
        pos = start if start != end else self.display.get_position()
        if len(current) - (end - start) + len(text) > MAX_EXPRESSION_LENGTH:
            return
        updated = current[:pos] + text + current[end if start != end else pos:]
        self.display.set_text(updated)
        self.display.set_position(pos + len(text))
        self.display.grab_focus()

    def on_equals(self, _widget) -> None:
        expression = self.display.get_text()
        if not expression.strip():
            return
        try:
            value = evaluate(expression, degree_mode=self.state.degree_mode)
            result = format_result(value)
        except ExpressionError as exc:
            self._add_history(expression, str(exc), error=True)
            return
        self.state.last_answer = value
        self._add_history(expression, result, error=False)
        self.display.set_text(result)

    def _add_history(self, expression: str, result: str, error: bool) -> None:
        if len(self.history_store.get_children()) >= HISTORY_LIMIT:
            self.history_store.remove(self.history_store.get_children()[0])
        row = Gtk.ListBoxRow()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for text, css_class in ((expression, "numdys-label"),
                                (result, "numdys-error" if error else "numdys-result")):
            label = Gtk.Label(label=text)
            label.set_halign(Gtk.Align.END)
            label.set_selectable(True)
            label.set_max_width_chars(40)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.get_style_context().add_class(css_class)
            content.pack_start(label, False, False, 0)
        row.add(content)
        self.history_store.add(row)
        row.show_all()

        def scroll_to_bottom() -> bool:
            adjustment = self.scroll.get_vadjustment()
            if adjustment is not None:
                adjustment.set_value(max(0.0, adjustment.get_upper() - adjustment.get_page_size()))
            return False

        GLib.idle_add(scroll_to_bottom)
