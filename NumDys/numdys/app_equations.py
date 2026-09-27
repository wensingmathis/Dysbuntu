import math

from gi.repository import Gtk

from .safe_eval import format_result


class EquationsApp(Gtk.Box):
    """Résolution d'équations : ax + b = 0 et ax² + bx + c = 0."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)
        self.state = state

        degree_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.radio_1 = Gtk.RadioButton.new_with_label_from_widget(None, "Degré 1 : ax + b = 0")
        self.radio_2 = Gtk.RadioButton.new_with_label_from_widget(self.radio_1, "Degré 2 : ax² + bx + c = 0")
        self.radio_1.connect("toggled", self.on_degree_changed)
        self.radio_2.connect("toggled", self.on_degree_changed)
        degree_box.pack_start(self.radio_1, False, False, 0)
        degree_box.pack_start(self.radio_2, False, False, 0)
        self.pack_start(degree_box, False, False, 0)

        self.coeff_grid = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.pack_start(self.coeff_grid, False, False, 0)

        self.entry_a = Gtk.Entry()
        self.entry_b = Gtk.Entry()
        self.entry_c = Gtk.Entry()
        for entry in (self.entry_a, self.entry_b, self.entry_c):
            entry.get_style_context().add_class("numdys-entry")
            entry.set_width_chars(6)

        solve_btn = Gtk.Button(label="Résoudre")
        solve_btn.get_style_context().add_class("equals")
        solve_btn.connect("clicked", self.on_solve)
        self.pack_start(solve_btn, False, False, 0)

        self.result_label = Gtk.Label(label="")
        self.result_label.set_line_wrap(True)
        self.result_label.get_style_context().add_class("numdys-result")
        self.pack_start(self.result_label, False, False, 0)

        self._build_coeff_grid()

    def _build_coeff_grid(self):
        for child in list(self.coeff_grid.get_children()):
            self.coeff_grid.remove(child)

        def label(text):
            widget = Gtk.Label(label=text)
            widget.get_style_context().add_class("numdys-label")
            return widget

        self.coeff_grid.attach(label("a ="), 0, 0, 1, 1)
        self.coeff_grid.attach(self.entry_a, 1, 0, 1, 1)
        self.coeff_grid.attach(label("b ="), 0, 1, 1, 1)
        self.coeff_grid.attach(self.entry_b, 1, 1, 1, 1)
        if self.radio_2.get_active():
            self.coeff_grid.attach(label("c ="), 0, 2, 1, 1)
            self.coeff_grid.attach(self.entry_c, 1, 2, 1, 1)
        self.coeff_grid.show_all()

    def on_degree_changed(self, _widget):
        self._build_coeff_grid()
        self.result_label.set_text("")

    def _parse(self, entry, default=0.0):
        text = entry.get_text().strip().replace(",", ".")
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return None

    def on_solve(self, _widget):
        a = self._parse(self.entry_a)
        b = self._parse(self.entry_b)
        if a is None or b is None:
            self.result_label.set_text("Coefficients invalides")
            return

        if self.radio_1.get_active():
            if a == 0:
                self.result_label.set_text(
                    "Pas de solution" if b != 0 else "Tout réel est solution"
                )
                return
            x = -b / a
            self.result_label.set_text(f"x = {format_result(x)}")
            return

        c = self._parse(self.entry_c)
        if c is None:
            self.result_label.set_text("Coefficients invalides")
            return

        if a == 0:
            self.result_label.set_text("a ne peut pas être nul pour une équation du 2nd degré")
            return

        delta = b * b - 4 * a * c
        if delta > 0:
            sqrt_delta = math.sqrt(delta)
            x1 = (-b - sqrt_delta) / (2 * a)
            x2 = (-b + sqrt_delta) / (2 * a)
            self.result_label.set_text(
                f"Δ = {format_result(delta)}\nx₁ = {format_result(x1)}   x₂ = {format_result(x2)}"
            )
        elif delta == 0:
            x0 = -b / (2 * a)
            self.result_label.set_text(f"Δ = 0\nSolution double : x₀ = {format_result(x0)}")
        else:
            sqrt_delta = math.sqrt(-delta)
            real = -b / (2 * a)
            imag = sqrt_delta / (2 * a)
            self.result_label.set_text(
                f"Δ = {format_result(delta)} < 0\n"
                f"x₁ = {format_result(real)} − {format_result(imag)}i   "
                f"x₂ = {format_result(real)} + {format_result(imag)}i"
            )
