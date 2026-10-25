"""Interface des équations du premier et du deuxième degré."""
from gi.repository import Gtk

from .math_models import EquationSolution, solve_linear, solve_quadratic
from .safe_eval import ExpressionError, format_result, parse_number


def _solution_text(solution: EquationSolution) -> str:
    status = solution.status
    if status == "all":
        return "Tout réel est solution."
    if status == "none":
        return "Aucune solution."
    if status == "one":
        return f"x = {format_result(solution.roots[0])}"
    # Le discriminant affiché est celui des coefficients originaux.
    delta = f"Δ = {solution.discriminant:.12g}\n"
    if status == "double":
        return delta + f"Racine double : x = {format_result(solution.roots[0])}"
    if status == "two":
        return (delta + f"x₁ = {format_result(solution.roots[0])}\n"
                + f"x₂ = {format_result(solution.roots[1])}")
    roots = solution.roots
    real, imag = roots[1].real, abs(roots[1].imag)
    return (delta + f"x₁ = {format_result(real)} − {format_result(imag)}i\n"
            + f"x₂ = {format_result(real)} + {format_result(imag)}i")


class EquationsApp(Gtk.Box):
    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)
        self.state = state
        chooser = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.radio_1 = Gtk.RadioButton.new_with_label_from_widget(None, "Degré 1")
        self.radio_2 = Gtk.RadioButton.new_with_label_from_widget(self.radio_1, "Degré 2")
        chooser.pack_start(self.radio_1, False, False, 0)
        chooser.pack_start(self.radio_2, False, False, 0)
        self.pack_start(chooser, False, False, 0)

        self.coeff_grid = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.pack_start(self.coeff_grid, False, False, 0)
        self.entries = {}
        for index, name in enumerate("abc"):
            label = Gtk.Label(label=f"{name} =")
            label.get_style_context().add_class("numdys-label")
            entry = Gtk.Entry()
            entry.set_max_length(64)
            entry.set_width_chars(8)
            entry.set_text("1" if name == "a" else "0")
            entry.get_style_context().add_class("numdys-entry")
            self.coeff_grid.attach(label, 0, index, 1, 1)
            self.coeff_grid.attach(entry, 1, index, 1, 1)
            self.entries[name] = (label, entry)

        button = Gtk.Button(label="Résoudre")
        button.get_style_context().add_class("equals")
        button.connect("clicked", self.on_solve)
        self.pack_start(button, False, False, 0)
        self.result_label = Gtk.Label(label="")
        self.result_label.set_line_wrap(True)
        self.result_label.set_selectable(True)
        self.result_label.get_style_context().add_class("numdys-result")
        self.pack_start(self.result_label, False, False, 0)
        for widget in self.entries["c"]:
            widget.set_no_show_all(True)
        self.radio_1.connect("toggled", self.on_degree_changed)
        self._update_coefficients()

    def _update_coefficients(self) -> None:
        is_quadratic = self.radio_2.get_active()
        for widget in self.entries["c"]:
            widget.set_visible(is_quadratic)

    def on_degree_changed(self, _widget) -> None:
        self._update_coefficients()
        self.result_label.set_text("")

    def on_solve(self, _widget) -> None:
        try:
            a = parse_number(self.entries["a"][1].get_text(), "a")
            b = parse_number(self.entries["b"][1].get_text(), "b")
            if self.radio_2.get_active():
                c = parse_number(self.entries["c"][1].get_text(), "c")
                solution = solve_quadratic(a, b, c)
            else:
                solution = solve_linear(a, b)
            self.result_label.set_text(_solution_text(solution))
            self.result_label.get_style_context().remove_class("numdys-error")
        except (ExpressionError, ZeroDivisionError, OverflowError) as exc:
            self.result_label.set_text(f"Erreur : {exc}")
            self.result_label.get_style_context().add_class("numdys-error")
