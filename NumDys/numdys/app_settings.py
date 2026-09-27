from gi.repository import Gtk


class SettingsApp(Gtk.Box):
    """Réglages généraux : mode degrés/radians pour la trigonométrie."""

    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.set_border_width(16)
        self.state = state

        label = Gtk.Label(label="Unité d'angle pour sin, cos, tan…")
        label.get_style_context().add_class("numdys-label")
        label.set_halign(Gtk.Align.START)
        self.pack_start(label, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.radio_rad = Gtk.RadioButton.new_with_label_from_widget(None, "Radians")
        self.radio_deg = Gtk.RadioButton.new_with_label_from_widget(self.radio_rad, "Degrés")
        self.radio_deg.set_active(state.degree_mode)
        self.radio_rad.set_active(not state.degree_mode)
        self.radio_rad.connect("toggled", self.on_toggled)
        box.pack_start(self.radio_rad, False, False, 0)
        box.pack_start(self.radio_deg, False, False, 0)
        self.pack_start(box, False, False, 0)

        info = Gtk.Label(
            label=(
                "Cette appli utilise la police OpenDyslexic sur toute "
                "l'interface. Si les caractères s'affichent avec une "
                "police système par défaut, vérifiez l'installation du "
                "paquet fonts-opendyslexic (voir le README)."
            )
        )
        info.set_line_wrap(True)
        info.get_style_context().add_class("numdys-label")
        info.set_halign(Gtk.Align.START)
        self.pack_start(info, False, False, 0)

    def on_toggled(self, _widget):
        self.state.degree_mode = self.radio_deg.get_active()
