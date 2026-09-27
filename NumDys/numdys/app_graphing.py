import math

from gi.repository import Gtk

from .safe_eval import evaluate, ExpressionError


class GraphingApp(Gtk.Box):
    """Traceur de courbes y = f(x), façon application Graphiques NumWorks."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_border_width(12)
        self.state = state

        self.expression = "sin(x)"
        self.xmin, self.xmax = -10.0, 10.0
        self.ymin, self.ymax = -6.0, 6.0
        self.error_message = None

        # --- Saisie de la fonction ---------------------------------------
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label="f(x) =")
        label.get_style_context().add_class("numdys-label")
        self.entry = Gtk.Entry()
        self.entry.set_text(self.expression)
        self.entry.get_style_context().add_class("numdys-entry")
        self.entry.connect("activate", self.on_expression_changed)
        entry_box.pack_start(label, False, False, 0)
        entry_box.pack_start(self.entry, True, True, 0)
        self.pack_start(entry_box, False, False, 0)

        # --- Zone de dessin ------------------------------------------------
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(360, 320)
        self.drawing_area.connect("draw", self.on_draw)
        self.pack_start(self.drawing_area, True, True, 0)

        self.error_label = Gtk.Label(label="")
        self.error_label.get_style_context().add_class("numdys-error")
        self.pack_start(self.error_label, False, False, 0)

        # --- Contrôles de vue -----------------------------------------------
        controls = Gtk.Grid(row_spacing=2, column_spacing=2, column_homogeneous=True)
        self.pack_start(controls, False, False, 0)

        buttons = [
            ("−", 0, 0, self.zoom_out),
            ("Réinit.", 0, 1, self.reset_view),
            ("+", 0, 2, self.zoom_in),
            ("◀", 1, 0, lambda _b: self.pan(-1, 0)),
            ("▲", 1, 1, lambda _b: self.pan(0, 1)),
            ("▶", 1, 2, lambda _b: self.pan(1, 0)),
        ]
        for label_text, row, col, handler in buttons:
            btn = Gtk.Button(label=label_text)
            btn.get_style_context().add_class("function")
            btn.connect("clicked", handler)
            controls.attach(btn, col, row, 1, 1)

        down_btn = Gtk.Button(label="▼")
        down_btn.get_style_context().add_class("function")
        down_btn.connect("clicked", lambda _b: self.pan(0, -1))
        controls.attach(down_btn, 1, 3, 1, 1)

    # ------------------------------------------------------------------
    def on_expression_changed(self, _widget):
        self.expression = self.entry.get_text()
        self.drawing_area.queue_draw()

    def zoom_in(self, _widget):
        self._zoom(0.7)

    def zoom_out(self, _widget):
        self._zoom(1.4)

    def _zoom(self, factor):
        cx = (self.xmin + self.xmax) / 2
        cy = (self.ymin + self.ymax) / 2
        half_w = (self.xmax - self.xmin) / 2 * factor
        half_h = (self.ymax - self.ymin) / 2 * factor
        self.xmin, self.xmax = cx - half_w, cx + half_w
        self.ymin, self.ymax = cy - half_h, cy + half_h
        self.drawing_area.queue_draw()

    def reset_view(self, _widget):
        self.xmin, self.xmax = -10.0, 10.0
        self.ymin, self.ymax = -6.0, 6.0
        self.drawing_area.queue_draw()

    def pan(self, dx_dir, dy_dir):
        step_x = (self.xmax - self.xmin) * 0.2 * dx_dir
        step_y = (self.ymax - self.ymin) * 0.2 * dy_dir
        self.xmin += step_x
        self.xmax += step_x
        self.ymin += step_y
        self.ymax += step_y
        self.drawing_area.queue_draw()

    # ------------------------------------------------------------------
    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Fond
        cr.set_source_rgb(0.10, 0.11, 0.13)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        def to_px(x, y):
            px = (x - self.xmin) / (self.xmax - self.xmin) * width
            py = height - (y - self.ymin) / (self.ymax - self.ymin) * height
            return px, py

        # Grille légère
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1)
        x_step = self._nice_step(self.xmax - self.xmin)
        y_step = self._nice_step(self.ymax - self.ymin)
        x = math.ceil(self.xmin / x_step) * x_step
        while x <= self.xmax:
            px, _ = to_px(x, 0)
            cr.move_to(px, 0)
            cr.line_to(px, height)
            x += x_step
        y = math.ceil(self.ymin / y_step) * y_step
        while y <= self.ymax:
            _, py = to_px(0, y)
            cr.move_to(0, py)
            cr.line_to(width, py)
            y += y_step
        cr.stroke()

        # Axes
        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.set_line_width(1.5)
        if self.ymin <= 0 <= self.ymax:
            _, py = to_px(0, 0)
            cr.move_to(0, py)
            cr.line_to(width, py)
        if self.xmin <= 0 <= self.xmax:
            px, _ = to_px(0, 0)
            cr.move_to(px, 0)
            cr.line_to(px, height)
        cr.stroke()

        # Courbe
        self.error_message = None
        cr.set_source_rgb(1.0, 0.72, 0.20)
        cr.set_line_width(2.5)
        pen_down = False
        prev_py = None
        samples = width  # un échantillon par pixel horizontal
        for i in range(samples + 1):
            data_x = self.xmin + (self.xmax - self.xmin) * i / samples
            try:
                data_y = evaluate(
                    self.expression, {"x": data_x}, degree_mode=self.state.degree_mode
                )
            except ExpressionError as exc:
                self.error_message = str(exc)
                pen_down = False
                continue
            if not isinstance(data_y, (int, float)) or math.isnan(data_y) or math.isinf(data_y):
                pen_down = False
                continue

            px, py = to_px(data_x, data_y)

            # Coupe le trait en cas de saut brutal (asymptote)
            if pen_down and prev_py is not None and abs(py - prev_py) > height * 1.5:
                pen_down = False

            if pen_down:
                cr.line_to(px, py)
            else:
                cr.move_to(px, py)
                pen_down = True
            prev_py = py
        cr.stroke()

        self.error_label.set_text(self.error_message or "")

    @staticmethod
    def _nice_step(span):
        raw_step = span / 10
        magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
        for multiple in (1, 2, 5, 10):
            step = magnitude * multiple
            if step >= raw_step:
                return step
        return magnitude * 10
