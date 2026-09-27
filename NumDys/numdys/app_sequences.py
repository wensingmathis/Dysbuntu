from gi.repository import Gtk

from .safe_eval import evaluate, format_result, ExpressionError


class SequencesApp(Gtk.Box):
    """Suites définies par récurrence : u(n+1) = f(u, n), à partir de u0."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state

        form = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.pack_start(form, False, False, 0)

        def label(text):
            widget = Gtk.Label(label=text)
            widget.get_style_context().add_class("numdys-label")
            return widget

        self.entry_formula = Gtk.Entry()
        self.entry_formula.set_text("u/2 + 1")
        self.entry_formula.get_style_context().add_class("numdys-entry")

        self.entry_u0 = Gtk.Entry()
        self.entry_u0.set_text("1")
        self.entry_u0.get_style_context().add_class("numdys-entry")
        self.entry_u0.set_width_chars(6)

        self.entry_n = Gtk.Entry()
        self.entry_n.set_text("10")
        self.entry_n.get_style_context().add_class("numdys-entry")
        self.entry_n.set_width_chars(6)

        form.attach(label("u(n+1) ="), 0, 0, 1, 1)
        form.attach(self.entry_formula, 1, 0, 2, 1)
        form.attach(label("u0 ="), 0, 1, 1, 1)
        form.attach(self.entry_u0, 1, 1, 1, 1)
        form.attach(label("Nombre de termes :"), 0, 2, 1, 1)
        form.attach(self.entry_n, 1, 2, 1, 1)

        hint = Gtk.Label(label="Utilisez « u » pour uₙ et « n » pour l'indice.")
        hint.get_style_context().add_class("numdys-label")
        hint.set_halign(Gtk.Align.START)
        self.pack_start(hint, False, False, 0)

        compute_btn = Gtk.Button(label="Calculer")
        compute_btn.get_style_context().add_class("equals")
        compute_btn.connect("clicked", self.on_compute)
        self.pack_start(compute_btn, False, False, 0)

        self.results_store = Gtk.ListBox()
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.add(self.results_store)
        self.pack_start(scroll, True, True, 0)

    def on_compute(self, _widget):
        for child in list(self.results_store.get_children()):
            self.results_store.remove(child)

        formula = self.entry_formula.get_text()
        try:
            u = float(self.entry_u0.get_text().strip().replace(",", "."))
            n_terms = int(self.entry_n.get_text().strip())
        except ValueError:
            self._add_row("Erreur : u0 ou N invalide", error=True)
            return

        if n_terms < 1 or n_terms > 500:
            self._add_row("Choisissez un nombre de termes entre 1 et 500", error=True)
            return

        self._add_row(f"u0 = {format_result(u)}", error=False)
        for index in range(1, n_terms + 1):
            try:
                u = evaluate(
                    formula, {"u": u, "n": index - 1}, degree_mode=self.state.degree_mode
                )
            except ExpressionError as exc:
                self._add_row(f"Erreur au terme {index} : {exc}", error=True)
                break
            self._add_row(f"u{index} = {format_result(u)}", error=False)

        self.results_store.show_all()

    def _add_row(self, text, error):
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=text)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("numdys-error" if error else "numdys-result")
        row.add(lbl)
        self.results_store.add(row)
