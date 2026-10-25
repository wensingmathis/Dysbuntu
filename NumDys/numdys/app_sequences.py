"""Écran des suites, avec compilation unique et nombre de termes limité."""
from gi.repository import Gtk

from .math_models import MAX_SEQUENCE_TERMS, sequence_terms
from .safe_eval import ExpressionError, MAX_EXPRESSION_LENGTH, format_result, parse_number


class SequencesApp(Gtk.Box):
    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state
        form = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.pack_start(form, False, False, 0)
        self.entry_formula = Gtk.Entry()
        self.entry_formula.set_text("u/2 + 1")
        self.entry_formula.set_max_length(MAX_EXPRESSION_LENGTH)
        self.entry_u0 = Gtk.Entry()
        self.entry_u0.set_text("1")
        self.entry_u0.set_max_length(64)
        self.entry_n = Gtk.Entry()
        self.entry_n.set_text("10")
        self.entry_n.set_max_length(4)
        for index, (caption, entry) in enumerate((
            ("u(n+1) =", self.entry_formula), ("u₀ =", self.entry_u0),
            ("Nombre d'itérations :", self.entry_n),
        )):
            label = Gtk.Label(label=caption)
            label.get_style_context().add_class("numdys-label")
            form.attach(label, 0, index, 1, 1)
            entry.get_style_context().add_class("numdys-entry")
            form.attach(entry, 1, index, 1, 1)
        hint = Gtk.Label(label=f"u : terme actuel, n : indice (1 à {MAX_SEQUENCE_TERMS} itérations)")
        hint.set_line_wrap(True)
        hint.set_halign(Gtk.Align.START)
        hint.get_style_context().add_class("numdys-label")
        self.pack_start(hint, False, False, 0)
        button = Gtk.Button(label="Calculer")
        button.get_style_context().add_class("equals")
        button.connect("clicked", self.on_compute)
        self.pack_start(button, False, False, 0)
        self.results_store = Gtk.ListBox()
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.add(self.results_store)
        self.pack_start(scroll, True, True, 0)

    def on_compute(self, _widget) -> None:
        for child in self.results_store.get_children():
            self.results_store.remove(child)
        try:
            initial = parse_number(self.entry_u0.get_text(), "u0")
            raw_count = self.entry_n.get_text().strip()
            if not raw_count.isdecimal():
                raise ExpressionError("N doit être un entier positif")
            count = int(raw_count)
            if count < 1 or count > MAX_SEQUENCE_TERMS:
                raise ExpressionError(f"N doit être entre 1 et {MAX_SEQUENCE_TERMS}")
            for index, value in sequence_terms(
                self.entry_formula.get_text(), initial, count, self.state.degree_mode
            ):
                self._add_row(f"u{index} = {format_result(value)}", error=False)
        except ExpressionError as exc:
            self._add_row(f"Erreur : {exc}", error=True)
        self.results_store.show_all()

    def _add_row(self, text: str, error: bool) -> None:
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        label.set_selectable(True)
        label.get_style_context().add_class("numdys-error" if error else "numdys-result")
        row.add(label)
        self.results_store.add(row)
