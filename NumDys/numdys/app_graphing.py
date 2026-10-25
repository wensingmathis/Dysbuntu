"""Traceur GTK/Cairo avec AST compilé une fois par fonction."""
from __future__ import annotations

import math

from gi.repository import Gtk

from .safe_eval import CompiledExpression, ExpressionError, MAX_EXPRESSION_LENGTH, compile_expression

MAX_SAMPLES = 1200  # reste fluide même sur un écran très large
MIN_SPAN = 1e-5
MAX_SPAN = 1e6
MAX_CENTER = 1e9


class GraphingApp(Gtk.Box):
    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state
        self.xmin, self.xmax = -10.0, 10.0
        self.ymin, self.ymax = -6.0, 6.0
        self.compiled: CompiledExpression = compile_expression("sin(x)", ("x",))

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label="f(x) =")
        label.get_style_context().add_class("numdys-label")
        input_row.pack_start(label, False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.set_text("sin(x)")
        self.entry.set_max_length(MAX_EXPRESSION_LENGTH)
        self.entry.get_style_context().add_class("numdys-entry")
        self.entry.connect("activate", self.on_expression_changed)
        input_row.pack_start(self.entry, True, True, 0)
        trace_button = Gtk.Button(label="Tracer")
        trace_button.connect("clicked", self.on_expression_changed)
        input_row.pack_start(trace_button, False, False, 0)
        self.pack_start(input_row, False, False, 0)

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(320, 260)
        self.drawing_area.connect("draw", self.on_draw)
        self.pack_start(self.drawing_area, True, True, 0)

        self.error_label = Gtk.Label(label="")
        self.error_label.set_line_wrap(True)
        self.error_label.get_style_context().add_class("numdys-error")
        self.pack_start(self.error_label, False, False, 0)

        controls = Gtk.Grid(row_spacing=2, column_spacing=2, column_homogeneous=True)
        self.pack_start(controls, False, False, 0)
        buttons = [
            ("−", 0, 0, self.zoom_out), ("Réinit.", 0, 1, self.reset_view),
            ("+", 0, 2, self.zoom_in), ("◀", 1, 0, lambda _: self.pan(-1, 0)),
            ("▲", 1, 1, lambda _: self.pan(0, 1)),
            ("▶", 1, 2, lambda _: self.pan(1, 0)),
            ("▼", 1, 3, lambda _: self.pan(0, -1)),
        ]
        for label_text, row, column, callback in buttons:
            button = Gtk.Button(label=label_text)
            button.get_style_context().add_class("function")
            button.connect("clicked", callback)
            controls.attach(button, column, row, 1, 1)

    def on_expression_changed(self, _widget) -> None:
        try:
            compiled = compile_expression(self.entry.get_text(), ("x",))
        except ExpressionError as exc:
            self.error_label.set_text(str(exc))
            return  # l'ancienne courbe reste visible
        self.compiled = compiled
        self.error_label.set_text("")
        self.drawing_area.queue_draw()

    def zoom_in(self, _widget) -> None:
        self._zoom(0.7)

    def zoom_out(self, _widget) -> None:
        self._zoom(1.4)

    def _zoom(self, factor: float) -> None:
        cx = (self.xmin + self.xmax) / 2
        cy = (self.ymin + self.ymax) / 2
        hx = (self.xmax - self.xmin) / 2 * factor
        hy = (self.ymax - self.ymin) / 2 * factor
        if not (MIN_SPAN <= 2 * hx <= MAX_SPAN and MIN_SPAN <= 2 * hy <= MAX_SPAN):
            return
        self.xmin, self.xmax = cx - hx, cx + hx
        self.ymin, self.ymax = cy - hy, cy + hy
        self.drawing_area.queue_draw()

    def reset_view(self, _widget) -> None:
        self.xmin, self.xmax = -10.0, 10.0
        self.ymin, self.ymax = -6.0, 6.0
        self.drawing_area.queue_draw()

    def pan(self, dx: int, dy: int) -> None:
        off_x = (self.xmax - self.xmin) * 0.2 * dx
        off_y = (self.ymax - self.ymin) * 0.2 * dy
        if max(abs(self.xmin + off_x), abs(self.xmax + off_x),
               abs(self.ymin + off_y), abs(self.ymax + off_y)) > MAX_CENTER:
            return
        self.xmin += off_x
        self.xmax += off_x
        self.ymin += off_y
        self.ymax += off_y
        self.drawing_area.queue_draw()

    @staticmethod
    def _nice_step(span: float) -> float:
        target = span / 10
        magnitude = 10 ** math.floor(math.log10(target))
        return next((magnitude * v for v in (1, 2, 5, 10) if magnitude * v >= target), magnitude * 10)

    def on_draw(self, widget, cr) -> bool:
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        if width <= 1 or height <= 1:
            return False
        cr.set_source_rgb(0.10, 0.11, 0.13)
        cr.paint()
        xspan = self.xmax - self.xmin
        yspan = self.ymax - self.ymin

        def project(x: float, y: float) -> tuple[float, float]:
            return (x - self.xmin) / xspan * width, height - (y - self.ymin) / yspan * height

        # Dessin limité à l'espace visible, sans boucle de grille non bornée.
        cr.save()
        cr.rectangle(0, 0, width, height)
        cr.clip()
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1)
        for is_x, lo, hi, span in ((True, self.xmin, self.xmax, xspan),
                                    (False, self.ymin, self.ymax, yspan)):
            step = self._nice_step(span)
            first = math.ceil(lo / step)
            last = math.floor(hi / step)
            for index in range(first, min(last + 1, first + 20)):
                coordinate = index * step
                if is_x:
                    px, _ = project(coordinate, 0)
                    cr.move_to(px, 0)
                    cr.line_to(px, height)
                else:
                    _, py = project(0, coordinate)
                    cr.move_to(0, py)
                    cr.line_to(width, py)
        cr.stroke()

        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.set_line_width(1.5)
        if self.ymin <= 0 <= self.ymax:
            _, py = project(0, 0)
            cr.move_to(0, py)
            cr.line_to(width, py)
        if self.xmin <= 0 <= self.xmax:
            px, _ = project(0, 0)
            cr.move_to(px, 0)
            cr.line_to(px, height)
        cr.stroke()

        cr.set_source_rgb(1.0, 0.72, 0.20)
        cr.set_line_width(2.5)
        pen_down = False
        previous_y = 0.0
        samples = min(MAX_SAMPLES, max(2, width))
        for index in range(samples + 1):
            x = self.xmin + xspan * index / samples
            try:
                y = self.compiled.evaluate({"x": x}, degree_mode=self.state.degree_mode)
            except ExpressionError:
                # Asymptote / domaine mathématique incorrect : interrompt le tracé.
                pen_down = False
                continue
            if not (self.ymin - yspan <= y <= self.ymax + yspan):
                pen_down = False
                continue
            px, py = project(x, y)
            if pen_down and abs(py - previous_y) <= height * 1.5:
                cr.line_to(px, py)
            else:
                cr.move_to(px, py)
            pen_down = True
            previous_y = py
        cr.stroke()
        cr.restore()
        return False
