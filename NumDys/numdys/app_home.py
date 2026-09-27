from gi.repository import Gtk


class HomeApp(Gtk.Box):
    """Grille d'icônes d'applications, façon écran d'accueil NumWorks."""

    def __init__(self, on_open):
        """on_open(app_name: str) est appelé quand une tuile est cliquée."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_border_width(24)

        title = Gtk.Label(label="NumDys")
        title.get_style_context().add_class("home-title")
        title.set_halign(Gtk.Align.START)
        self.pack_start(title, False, False, 0)

        grid = Gtk.Grid(row_spacing=14, column_spacing=14, column_homogeneous=True)
        self.pack_start(grid, True, True, 0)

        apps = [
            ("calculatrice", "🖩\nCalculs"),
            ("graphiques", "📈\nGraphiques"),
            ("equations", "𝑥²\nÉquations"),
            ("suites", "𝑢ₙ\nSuites"),
            ("reglages", "⚙\nRéglages"),
        ]

        for index, (app_id, label) in enumerate(apps):
            row, col = divmod(index, 3)
            tile = Gtk.Button(label=label)
            tile.get_style_context().add_class("app-tile")
            tile.connect("clicked", lambda _b, a=app_id: on_open(a))
            grid.attach(tile, col, row, 1, 1)
