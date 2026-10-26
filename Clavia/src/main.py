#!/usr/bin/env python3
"""Clavia : jeu de frappe AZERTY natif pour Linux (GTK 4)."""
import logging
from functools import wraps
import math
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, GLib, Gtk, Pango

from content import LESSONS, SPRINT_WORDS
from engine import (compute_metrics, consecutive_days, level_from_xp, matches_target,
                    next_expected, rich_target, safe_volume, same_character)
from storage import Storage, StorageError
from audio import SoundManager

LOGGER = logging.getLogger(__name__)
BASE = Path(__file__).resolve().parent.parent
CSS_FILE = BASE / 'assets' / 'style.css'
LIGHT_CSS_FILE = BASE / 'assets' / 'style-light.css'
ROWS = (
    ('²', '&', 'é', '"', "'", '(', '-', 'è', '_', 'ç', 'à', ')', '='),
    ('a', 'z', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '^', '$'),
    ('q', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'ù', '*'),
    ('<', 'w', 'x', 'c', 'v', 'b', 'n', ',', ';', ':', '!'),
    ('ESPACE',),
)


# Disposition physique AZERTY français (France, touches classiques).
# Chaque touche = (inscription, largeur relative, caractère utilisé pour le guidage).
KEYBOARD_LAYOUT = (
    [('Échap', 1.35, None), ('²', 1, '²'), ('&\n1', 1, '&'), ('é\n2', 1, 'é'), ('\"\n3', 1, '"'), ("'\n4", 1, "'"), ('(\n5', 1, '('), ('-\n6', 1, '-'), ('è\n7', 1, 'è'), ('_\n8', 1, '_'), ('ç\n9', 1, 'ç'), ('à\n0', 1, 'à'), (')\n°', 1, ')'), ('=\n+', 1, '='), ('⌫', 1.5, 'RETOUR')],
    [('Tab', 1.55, None), *[(c, 1, c) for c in 'azertyuiop'], ('^\n¨', 1, '^'), ('$\n£', 1, '$'), ('Entrée', 1.6, None)],
    [('Verr Maj', 1.85, None), *[(c, 1, c) for c in 'qsdfghjklm'], ('ù\n%', 1, 'ù'), ('*\nµ', 1, '*'), ('↵', 1.5, None)],
    [('Maj', 1.5, None), ('<\n>', 1, '<'), *[(c, 1, c) for c in 'wxcvbn'], (',\n?', 1, ','), (';\n.', 1, ';'), (':\n/', 1, ':'), ('!\n§', 1, '!'), ('Maj', 2.2, None)],
    [('Ctrl', 1.3, None), ('Super', 1.3, None), ('Alt', 1.2, None), ('ESPACE', 5.8, 'ESPACE'), ('AltGr', 1.35, None), ('Fn', 1.0, None), ('Ctrl', 1.3, None)],
)


def widget_label(text='', css=None, wrap=False, align=0.0):
    label = Gtk.Label(label=str(text))
    label.set_xalign(align)
    label.set_wrap(wrap)
    if wrap:
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if css:
        label.add_css_class(css)
    return label


def make_box(vertical=True, gap=12, css=None):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,
                  spacing=gap)
    if css:
        box.add_css_class(css)
    return box


def add_button(parent, label, callback, css='secondary', expand=False):
    """Boutons GTK natifs : CTA avec flèche ou action secondaire discrète.

    GTK4 n'utilise pas les pseudo-éléments HTML (::before, svg) : les
    éléments visuels sont de vrais widgets pour rester accessibles.
    """
    button = Gtk.Button()
    button.add_css_class(css)
    if css == 'primary':
        button.add_css_class('arrow-button')
        inside = make_box(False, 12)
        inside.set_halign(Gtk.Align.CENTER)
        text = widget_label(label, 'button-caption')
        arrow = widget_label('→', 'button-arrow')
        inside.append(text)
        inside.append(arrow)
        button.set_child(inside)
        hover = Gtk.EventControllerMotion()
        hover.connect('enter', lambda *_: arrow.add_css_class('arrow-hover'))
        hover.connect('leave', lambda *_: arrow.remove_css_class('arrow-hover'))
        button.add_controller(hover)
    else:
        button.set_label(label)
    def clicked(*_):
        app = getattr(parent.get_root(), 'get_application', lambda: None)()
        if app is not None and hasattr(app, 'audio'):
            app.audio.play('button_click')
        callback()
    button.connect('clicked', clicked)
    if expand:
        button.set_hexpand(True)
    parent.append(button)
    return button


def add_continue_button(parent, label, callback):
    """CTA Continuer : animation Uiverse adaptée aux widgets GTK4.

    Pas de surcharge graphique, minuterie ou emoji. Le bouton reste accessible
    au clavier et conserve le comportement de lancement de leçon.
    """
    button = Gtk.Button()
    button.add_css_class('continue-motion')
    button.set_tooltip_text(label)
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(130)
    stack.set_hexpand(True)

    normal = make_box(False, 12, 'continue-face')
    normal.set_halign(Gtk.Align.CENTER)
    normal.append(widget_label(label, 'continue-text'))
    normal.append(widget_label('→', 'continue-arrow'))

    highlighted = make_box(False, 12, 'continue-face')
    highlighted.set_halign(Gtk.Align.CENTER)
    highlighted.append(widget_label('Jouer maintenant', 'continue-text'))
    highlighted.append(widget_label('→', 'continue-arrow-large'))

    stack.add_named(normal, 'normal')
    stack.add_named(highlighted, 'hover')
    stack.set_visible_child_name('normal')
    button.set_child(stack)

    hover = Gtk.EventControllerMotion()
    hover.connect('enter', lambda *_: stack.set_visible_child_name('hover'))
    hover.connect('leave', lambda *_: stack.set_visible_child_name('normal'))
    button.add_controller(hover)

    def clicked(*_):
        root = button.get_root()
        app = root.get_application() if root is not None and hasattr(root, 'get_application') else None
        if app is not None and hasattr(app, 'audio'):
            app.audio.play('button_click')
        callback()

    button.connect('clicked', clicked)
    parent.append(button)
    return button


def add_exit_button(parent, callback):
    """Bouton retour AKAspidey01 : le fond ambre s'étend au survol.

    Animation bornée à 250 ms, déclenchée seulement à l'entrée/sortie,
    sans changement de page, données ou styles des autres composants.
    """
    button = Gtk.Button()
    button.add_css_class('exit-motion')
    button.set_tooltip_text('Quitter le niveau et revenir au parcours')
    button.set_size_request(188, 54)

    # La couche inférieure se déploie ; le texte reste au premier plan.
    overlay = Gtk.Overlay()
    background = make_box(False, 0, 'exit-background')
    background.set_size_request(180, 46)
    fill = Gtk.Box()
    fill.add_css_class('exit-fill')
    fill.set_size_request(45, 46)
    background.append(fill)
    overlay.set_child(background)

    foreground = make_box(False, 0, 'exit-foreground')
    foreground.set_halign(Gtk.Align.FILL)
    foreground.set_valign(Gtk.Align.FILL)
    arrow_cell = make_box(False, 0, 'exit-arrow-cell')
    arrow_cell.set_size_request(45, 46)
    arrow_cell.append(widget_label('←', 'exit-arrow'))
    foreground.append(arrow_cell)
    label = widget_label('Quitter', 'exit-text')
    label.set_hexpand(True)
    label.set_halign(Gtk.Align.CENTER)
    label.set_valign(Gtk.Align.CENTER)
    foreground.append(label)
    overlay.add_overlay(foreground)
    button.set_child(overlay)

    # GTK4 n'anime pas les dimensions automatiquement avec une transition CSS.
    # On interpole uniquement la largeur du fond, ~16 frames pendant 250 ms.
    start_width = 45
    full_width = 180
    animation = {'source': None, 'from': start_width, 'to': start_width,
                 'started': 0.0, 'width': start_width}

    def advance():
        elapsed = (time.monotonic() - animation['started']) / 0.25
        fraction = min(1.0, max(0.0, elapsed))
        eased = 1.0 - (1.0 - fraction) ** 3
        width = round(animation['from'] + (animation['to'] - animation['from']) * eased)
        animation['width'] = width
        fill.set_size_request(width, 46)
        if fraction >= 1.0 or button.get_parent() is None:
            animation['source'] = None
            return False
        return True

    def animate(target):
        if animation['source'] is not None:
            GLib.source_remove(animation['source'])
            animation['source'] = None
        animation['from'] = animation['width']
        animation['to'] = target
        animation['started'] = time.monotonic()
        if animation['from'] != target:
            animation['source'] = GLib.timeout_add(16, advance)
        if target == full_width:
            button.add_css_class('exit-hovered')
        else:
            button.remove_css_class('exit-hovered')

    motion = Gtk.EventControllerMotion()
    motion.connect('enter', lambda *_: animate(full_width))
    motion.connect('leave', lambda *_: animate(start_width))
    button.add_controller(motion)

    def clicked(*_):
        if animation['source'] is not None:
            GLib.source_remove(animation['source'])
            animation['source'] = None
        root = button.get_root()
        app = root.get_application() if root and hasattr(root, 'get_application') else None
        if app is not None and hasattr(app, 'audio'):
            app.audio.play('button_click')
        callback()

    button.connect('clicked', clicked)
    parent.append(button)
    return button


def add_sprint_button(parent, callback):
    """Bouton Sprint façon Uiverse / Voxybuns, GTK4 natif.

    Isolé du style des autres boutons et sans nouveaux timers.
    La marge du dessus représente l'enfoncement physique de la touche.
    """
    button = Gtk.Button()
    button.add_css_class('sprint-relief')
    button.set_tooltip_text('Lancer le défi chronométré de 60 secondes')
    top = make_box(False, 0, 'sprint-top')
    top.set_halign(Gtk.Align.FILL)
    top.set_valign(Gtk.Align.CENTER)
    label = widget_label('Sprint de 60 secondes', 'sprint-label')
    label.set_hexpand(True)
    label.set_halign(Gtk.Align.CENTER)
    top.append(label)
    button.set_child(top)

    def clicked(*_):
        root = button.get_root()
        app = root.get_application() if root is not None and hasattr(root, 'get_application') else None
        if app is not None and hasattr(app, 'audio'):
            app.audio.play('button_click')
        callback()

    button.connect('clicked', clicked)
    parent.append(button)
    return button


def clear(box):
    while box.get_first_child() is not None:
        box.remove(box.get_first_child())


def storage_guard(callback):
    """Report recoverable SQLite read failures instead of breaking GTK callbacks."""
    @wraps(callback)
    def guarded(self, *args, **kwargs):
        try:
            return callback(self, *args, **kwargs)
        except StorageError as exc:
            if callback.__name__ == 'finish':
                self.new_page()
            self.show_storage_error(callback.__name__, exc)
            return False
    return guarded


class Flame(Gtk.Picture):
    """Flamme exacte extraite du GIF fourni, avec fond transparent."""

    def __init__(self, active=True):
        super().__init__()
        self.set_filename(str(BASE / 'assets' / 'flamme-streak.png'))
        self.set_can_shrink(True)
        self.set_size_request(35, 39)
        self.set_content_fit(Gtk.ContentFit.CONTAIN)



class ThemeSwitch(Gtk.Button):
    """Bouton jour/nuit natif GTK : ciel, nuages, étoiles, soleil et lune dessinés en 2D."""

    def __init__(self, dark, callback):
        super().__init__()
        self.dark = dark
        self.callback = callback
        self.set_tooltip_text('Passer au thème clair' if dark else 'Passer au thème sombre')
        self.add_css_class('theme-toggle')
        self.set_focusable(True)
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_content_width(110)
        self.canvas.set_content_height(48)
        self.canvas.set_draw_func(self.draw)
        self.set_child(self.canvas)
        self.connect('clicked', self.clicked)

    def clicked(self, *_):
        self.dark = not self.dark
        self.set_tooltip_text('Passer au thème clair' if self.dark else 'Passer au thème sombre')
        self.canvas.queue_draw()
        self.callback(self.dark)

    def draw(self, _area, cr, w, h):
        import math
        # Capsule mate : nuit à droite, jour à gauche.
        cr.set_source_rgb(*( (0.17, 0.26, 0.38) if self.dark else (0.62, 0.82, 0.93)))
        cr.new_sub_path()
        cr.arc(24, 24, 21, math.pi/2, 3*math.pi/2)
        cr.arc(86, 24, 21, -math.pi/2, math.pi/2)
        cr.close_path(); cr.fill()
        if self.dark:
            cr.set_source_rgb(0.97, 0.97, 0.86)
            for x,y,r in ((19,12,1.7),(34,19,1.2),(48,10,1.4),(51,34,1.2),(16,34,1.0)):
                cr.arc(x,y,r,0,2*math.pi); cr.fill()
        else:
            cr.set_source_rgba(1,1,1,0.82)
            for x,y,r in ((64,32,9),(75,30,12),(87,33,8)):
                cr.arc(x,y,r,0,2*math.pi); cr.fill()
        knob_x = 82 if self.dark else 28
        cr.set_source_rgba(0.07,0.08,0.10,0.20)
        cr.arc(knob_x,25,19,0,2*math.pi); cr.fill()
        cr.set_source_rgb(0.96,0.96,0.93)
        cr.arc(knob_x,23,19,0,2*math.pi); cr.fill()
        if self.dark:
            cr.set_source_rgb(0.75,0.76,0.77)
            cr.arc(knob_x+3,22,11,0,2*math.pi); cr.fill()
            cr.set_source_rgb(0.96,0.96,0.93)
            cr.arc(knob_x-2,19,10,0,2*math.pi); cr.fill()
        else:
            cr.set_source_rgb(0.95,0.68,0.12)
            cr.arc(knob_x,23,11,0,2*math.pi); cr.fill()
            for i in range(8):
                theta=i*math.pi/4
                cr.set_line_width(1.6)
                cr.move_to(knob_x+13*math.cos(theta),23+13*math.sin(theta))
                cr.line_to(knob_x+15*math.cos(theta),23+15*math.sin(theta))
                cr.stroke()

class SpeedGraph(Gtk.DrawingArea):
    """Courbe minimaliste des vitesses enregistrées, sans dépendance externe."""

    def __init__(self, sessions, dark=True):
        super().__init__()
        self.dark = dark
        self.speeds = [row['cpm'] for row in sessions]
        self.set_content_width(760)
        self.set_content_height(185)
        self.set_hexpand(True)
        self.set_draw_func(self.draw_graph)

    def draw_graph(self, _area, cr, width, height):
        if not self.speeds:
            return
        left, top, right, bottom = 18, 18, width - 18, height - 22
        chart_height = bottom - top
        min_speed = 0
        max_speed = max(40, max(self.speeds) * 1.15)
        for n in range(4):
            y = bottom - chart_height * n / 3
            cr.set_source_rgb(*( (0.24, 0.24, 0.27) if self.dark else (0.85, 0.86, 0.87)))
            cr.set_line_width(1)
            cr.move_to(left, y)
            cr.line_to(right, y)
            cr.stroke()
        points = []
        for i, value in enumerate(self.speeds):
            x = left + (right - left) * i / max(1, len(self.speeds) - 1)
            y = bottom - chart_height * (value - min_speed) / max_speed
            points.append((x, y))
        cr.set_source_rgb(*( (226 / 255, 183 / 255, 20 / 255) if self.dark else (176 / 255, 132 / 255, 0)))
        cr.set_line_width(2)
        for i, (x, y) in enumerate(points):
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        if len(points) >= 2:
            cr.stroke()
        for x, y in points:
            cr.arc(x, y, 2.7, 0, 2 * math.pi)
            cr.fill()



class Clavia(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='fr.clavia.azerty')
        self.db = Storage()
        self.large = self.db.preference('large', '0') == '1'
        self.dark = self.db.preference('dark', '1') == '1'
        self.motion = self.db.preference('motion', '1') == '1'
        self.show_keys = self.db.preference('keyboard', '1') == '1'
        self.dyslexic = self.db.preference('dyslexic', '0') == '1'
        self.dyslexic_available = self.check_font()
        self.audio = SoundManager(BASE / 'assets' / 'sounds',
                                  enabled=self.db.preference('sounds', '1') == '1',
                                  keyboard=self.db.preference('keyboard_sounds', '0') == '1',
                                  rewards=self.db.preference('reward_sounds', '1') == '1',
                                  volume=safe_volume(self.db.preference('sound_volume', '55')))
        self.timer_id = None
        self.flame_id = None
        self.key_pressed_timeout = None
        self.lesson = None
        self.finished = False
        self.sprint = False
        self.started = None
        self.prompts = ()
        self.stage = 0
        self.attempts = 0
        self.errors = 0
        self.completed_chars = 0
        self.completed_words = 0
        self.key_labels = []
        self.last_pressed_key = None
        self.exercise_token = 0
        self.pending_transition = False

    def show_storage_error(self, operation, exc):
        """Keep the window usable and never pretend a failed write succeeded."""
        LOGGER.error('Erreur de sauvegarde (%s): %s', operation, exc)
        if hasattr(self, 'page'):
            warning = widget_label(f'Sauvegarde impossible ({operation}). Vérifie les droits et l’espace disque.',
                                   'notice', True)
            self.page.prepend(warning)

    def check_font(self):
        try:
            result = subprocess.run(['fc-list', '-f', '%{family}\n'],
                                    capture_output=True, text=True, timeout=2, check=False)
            return 'opendyslexic' in result.stdout.lower()
        except (OSError, subprocess.TimeoutExpired):
            return False

    def do_activate(self):
        if hasattr(self, 'window'):
            self.window.present()
            return
        # Demande également une décoration de fenêtre sombre au thème système.
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property('gtk-application-prefer-dark-theme', self.dark)
        self.window = Gtk.ApplicationWindow(application=self, title='Clavia — Apprendre le clavier AZERTY')
        self.window.set_default_size(1120, 800)
        self.window.set_size_request(790, 580)
        self.base = make_box(gap=0)
        self.window.set_child(self.base)
        self.create_header()
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_vexpand(True)
        self.base.append(self.scroller)
        self.page = make_box(gap=20, css='page')
        self.page.set_margin_top(30)
        self.page.set_margin_bottom(45)
        self.page.set_margin_start(40)
        self.page.set_margin_end(40)
        self.page.set_halign(Gtk.Align.CENTER)
        self.page.set_size_request(740, -1)
        self.scroller.set_child(self.page)
        self.apply_theme()
        self.home()
        self.window.present()

    def create_header(self):
        header = make_box(False, gap=10, css='topbar')
        header.set_margin_start(32)
        header.set_margin_end(32)
        header.set_margin_top(13)
        header.set_margin_bottom(13)
        self.base.append(header)
        self.header = header
        name = widget_label('CLAVIA', 'brand')
        header.append(name)
        hint = widget_label('APPRENDRE À TAPER', 'brand-caption')
        header.append(hint)
        spacer = make_box(False)
        spacer.set_hexpand(True)
        header.append(spacer)
        add_button(header, 'Parcours', self.home, 'nav')
        add_button(header, 'Statistiques', self.stats, 'nav')
        add_button(header, 'Paramètres', self.settings, 'nav')
        self.theme_button = ThemeSwitch(self.dark, self.change_theme)
        header.append(self.theme_button)

    def apply_theme(self):
        """Palettes Slate sombre / claire, sans toucher aux préférences de lecture."""
        if hasattr(self, 'provider'):
            Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), self.provider)
        try:
            raw = (CSS_FILE if self.dark else LIGHT_CSS_FILE).read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            LOGGER.error('Feuille CSS inaccessible : %s', exc)
            raw = '.page { padding: 12px; } .prompt { font-size: 18px; }'
        for pattern in ('geo', 'paper', 'grid'):
            tile = BASE / 'assets' / 'backgrounds' / f'{pattern}-{"dark" if self.dark else "light"}.png'
            raw = raw.replace(f'__CLAVIA_BG_{pattern.upper()}__', tile.as_uri())
        self.provider = Gtk.CssProvider()
        self.provider.load_from_string(raw)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        if hasattr(self, 'window'):
            self.window.set_property('title', 'Clavia — AZERTY')
            for widget in (self.window,):
                if self.large:
                    widget.add_css_class('large-text')
                else:
                    widget.remove_css_class('large-text')
                if self.dyslexic and self.dyslexic_available:
                    widget.add_css_class('dyslexic-font')
                else:
                    widget.remove_css_class('dyslexic-font')


    def change_theme(self, dark):
        self.dark = dark
        try:
            self.db.set_preference('dark', '1' if dark else '0')
        except StorageError as exc:
            self.show_storage_error('thème', exc)
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property('gtk-application-prefer-dark-theme', dark)
        self.apply_theme()
        if hasattr(self, 'theme_button') and self.theme_button.dark != dark:
            self.theme_button.dark = dark
            self.theme_button.canvas.queue_draw()

    def stop_timers(self):
        for field in ('timer_id', 'flame_id', 'key_pressed_timeout'):
            timer = getattr(self, field)
            if timer is not None:
                GLib.source_remove(timer)
                setattr(self, field, None)

    def clear_level_background(self):
        for css in ('level-bg-geo', 'level-bg-paper', 'level-bg-grid'):
            self.scroller.remove_css_class(css)

    def apply_level_background(self, lesson=None, sprint=False):
        """Un motif sur le viewport entier, alterné entre les leçons."""
        self.clear_level_background()
        if sprint:
            pattern = 'grid'
        elif lesson is not None:
            pattern = ('geo', 'paper', 'grid')[(lesson.id - 1) % 3]
        else:
            return
        self.scroller.add_css_class('level-bg-' + pattern)

    def new_page(self):
        self.stop_timers()
        self.finished = True
        self.exercise_token += 1  # Invalidates pending idle callbacks from the previous page.
        self.pending_transition = False
        clear(self.page)
        self.clear_level_background()
        self.header.set_visible(True)
        self.scroller.get_vadjustment().set_value(0)

    def panel(self, parent=None, css='panel', gap=12):
        item = make_box(gap=gap, css=css)
        (parent or self.page).append(item)
        return item

    def page_title(self, title, description=''):
        self.page.append(widget_label(title, 'page-title'))
        if description:
            self.page.append(widget_label(description, 'subtitle', True))


    @storage_guard
    def home(self):
        self.new_page()
        summ = self.db.summary()
        streak = consecutive_days(self.db.active_days())
        unlocked = self.db.unlocked_id()
        lvl = level_from_xp(summ['xp'])

        intro = self.panel(css='hero')
        intro.append(widget_label('LE PARCOURS AZERTY', 'eyebrow'))
        intro.append(widget_label('Apprends. Progresse. Recommence.', 'hero-title', True))
        intro.append(widget_label('Commence par les mots, découvre les phrases, puis écris des textes complets. '
                                  'Ta précision et ta vitesse te font gagner des points.', 'subtitle', True))
        actions = make_box(False, 12)
        intro.append(actions)
        next_lesson = LESSONS[min(unlocked, len(LESSONS)) - 1]
        add_continue_button(actions, f'Continuer : niveau {next_lesson.id}',
                            lambda l=next_lesson: self.start_lesson(l))
        add_sprint_button(actions, self.start_sprint)

        # Deux colonnes : l'ancienne rangée horizontale faisait disparaître
        # certaines cartes hors de la fenêtre (défilement horizontal désactivé).
        statsgrid = Gtk.Grid()
        statsgrid.set_column_spacing(12)
        statsgrid.set_row_spacing(12)
        statsgrid.set_column_homogeneous(True)
        self.page.append(statsgrid)
        cards = (
            ('NIVEAU', str(lvl), f'{summ["xp"]} XP au total', False),
            ('JOURS DE SUITE', str(streak),
             'Entraînement régulier' if streak else 'Termine une leçon pour commencer', True),
            ('LEÇONS VALIDÉES', f'{min(unlocked - 1, len(LESSONS))} / {len(LESSONS)}',
             'Du mot au texte', False),
            ('OBJECTIF DU JOUR', f'{min(3, self.db.today_sessions())} / 3',
             '3 exercices par jour', False),
        )
        for index, (heading, value, foot, has_flame) in enumerate(cards):
            card = self.stat_card(None, heading, value, foot, flame=has_flame)
            statsgrid.attach(card, index % 2, index // 2, 1, 1)

        self.page.append(widget_label('Ton parcours', 'section-title'))
        self.page.append(widget_label('Termine une leçon pour débloquer la suivante. '
                                      'Tu peux refaire tes leçons pour améliorer ton record.', 'subtitle', True))
        completed = self.db.completed_ids()
        bests = self.db.best_by_lesson()
        for kind in ('Mots', 'Phrases', 'Textes', 'Situations', 'Précision', 'Maîtrise'):
            section = self.panel(gap=13)
            heading = make_box(False, 10)
            section.append(heading)
            heading.append(widget_label(kind.upper(), 'chapter'))
            heading.append(widget_label({'Mots': '01', 'Phrases': '02', 'Textes': '03', 'Situations': '04', 'Précision': '05', 'Maîtrise': '06'}[kind], 'chapter-number'))
            for lesson in LESSONS:
                if lesson.kind != kind:
                    continue
                available = lesson.id <= unlocked
                best = bests.get(lesson.id, {'best_score': None, 'stars': None, 'best_cpm': None})
                card = make_box(False, 12, css='lesson-card')
                if not available:
                    card.add_css_class('locked')
                section.append(card)
                roundel = widget_label(f'{lesson.id:02d}', 'number-pill')
                roundel.set_size_request(47, 47)
                card.append(roundel)
                labels = make_box(gap=3)
                labels.set_hexpand(True)
                card.append(labels)
                labels.append(widget_label(lesson.title, 'lesson-title'))
                labels.append(widget_label(lesson.description, 'lesson-description', True))
                if lesson.id in completed:
                    detail = f'Validée  |  {best["stars"]} / 3 étoiles  |  Record : {best["best_cpm"]} car/min'
                elif available:
                    detail = 'PROCHAINE LEÇON'
                else:
                    detail = 'À DÉBLOQUER'
                labels.append(widget_label(detail, 'mini-accent' if available else 'muted'))
                button = add_button(card, 'Rejouer' if lesson.id in completed else
                                    ('Jouer' if available else 'Verrouillée'),
                                    lambda l=lesson: self.start_lesson(l),
                                    'secondary' if lesson.id in completed else 'primary')
                button.set_sensitive(available)

    def stat_card(self, parent, heading, value, foot, flame=False):
        # parent=None permet de placer la carte dans un Gtk.Grid.
        item = make_box(gap=6, css='stat-card')
        item.set_hexpand(True)
        if parent is not None:
            parent.append(item)
        item.append(widget_label(heading, 'small-stat'))
        value_row = make_box(False, 8)
        item.append(value_row)
        if flame:
            self.flame = Flame(self.motion)
            value_row.append(self.flame)
        value_row.append(widget_label(value, 'big-stat'))
        item.append(widget_label(foot, 'muted', True))
        return item

    @storage_guard
    def start_lesson(self, lesson):
        if lesson.id > self.db.unlocked_id():
            self.home()
            return
        self.lesson = lesson
        self.sprint = False
        self.prompts = lesson.prompts
        self.start_exercise()

    def start_sprint(self):
        self.lesson = None
        self.sprint = True
        self.prompts = tuple(random.choices(SPRINT_WORDS, k=200))
        self.start_exercise()

    def start_exercise(self):
        self.new_page()
        self.apply_level_background(self.lesson, self.sprint)
        self.header.set_visible(False)
        self.finished = False
        self.stage = 0
        self.attempts = 0
        self.errors = 0
        self.completed_chars = 0
        self.completed_words = 0
        self.started = None
        self.last_elapsed = 0.0
        self.current_length = 0
        self.key_labels = []
        self.last_pressed_key = None

        # En mode frappe : texte et métriques uniquement, sans navigation latérale.
        top = make_box(False, gap=12)
        self.page.append(top)
        heading = make_box(gap=4)
        heading.set_hexpand(True)
        top.append(heading)
        heading.append(widget_label('DÉFI / 60 SECONDES' if self.sprint else
                                    f'PARCOURS / {self.lesson.kind.upper()} / {self.lesson.id:02d}', 'eyebrow'))
        heading.append(widget_label('Sprint' if self.sprint else self.lesson.title,
                                    'page-title', True))
        add_exit_button(top, self.home)

        # Barre légère avec temps, vitesse, précision et points.
        status = make_box(False, gap=12, css='exercise-status')
        self.page.append(status)
        self.stage_label = widget_label('', 'subtitle')
        self.stage_label.set_hexpand(True)
        self.stage_label.set_valign(Gtk.Align.CENTER)
        status.append(self.stage_label)
        self.clock_label = self.exercise_metric(status, 'TEMPS', '00:00', True)
        self.live_speed = self.exercise_metric(status, 'CAR./MIN', '0')
        self.live_accuracy = self.exercise_metric(status, 'PRÉCISION', '100 %')
        self.live_score = self.exercise_metric(status, 'POINTS', '0')
        self.bar = Gtk.ProgressBar()
        self.bar.add_css_class('progress')
        self.page.append(self.bar)

        target_panel = self.panel(css='exercise-card', gap=14)
        target_panel.append(widget_label('REPRODUIS CE TEXTE', 'eyebrow'))
        self.target_label = Gtk.Label()
        self.target_label.add_css_class('prompt')
        self.target_label.set_wrap(True)
        self.target_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.target_label.set_xalign(0)
        self.target_label.set_selectable(False)
        target_panel.append(self.target_label)
        target_panel.append(widget_label('ÉCRIS ICI', 'eyebrow'))
        writing = make_box(css='writing', gap=0)
        target_panel.append(writing)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(15)
        self.text_view.set_right_margin(15)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        self.text_view.set_size_request(-1, 90)
        self.text_view.add_css_class('input-text')
        writing.append(self.text_view)
        self.buffer = self.text_view.get_buffer()
        self.buffer.connect('insert-text', self.on_insert)
        self.buffer.connect('changed', self.on_changed)
        ctl = Gtk.EventControllerKey()
        ctl.connect('key-pressed', self.on_key_pressed)
        self.text_view.add_controller(ctl)
        self.feedback = widget_label('Le chrono démarre dès la première lettre.', 'subtitle', True)
        target_panel.append(self.feedback)

        if self.show_keys:
            keyboard_panel = self.panel(css='keyboard-panel', gap=10)
            keyboard_panel.append(widget_label('CLAVIER AZERTY', 'eyebrow'))
            self.keys_hint = widget_label('La prochaine touche à utiliser est surlignée.', 'subtitle')
            keyboard_panel.append(self.keys_hint)
            board = make_box(gap=5, css='keyboard-body')
            board.set_halign(Gtk.Align.CENTER)
            keyboard_panel.append(board)
            for row in KEYBOARD_LAYOUT:
                line = make_box(False, 4, css='keyboard-row')
                line.set_halign(Gtk.Align.CENTER)
                board.append(line)
                for title, unit, char in row:
                    key = widget_label(title, 'keycap')
                    key.add_css_class('keyboard-key')
                    if unit >= 1.3:
                        key.add_css_class('key-modifier')
                    if char == 'ESPACE':
                        key.add_css_class('key-space')
                    key.set_justify(Gtk.Justification.CENTER)
                    key.set_xalign(.5)
                    key.set_size_request(round(34 * unit + 5 * (unit - 1)), 45)
                    line.append(key)
                    if char:
                        self.key_labels.append((char, key))
        self.update_prompt()
        self.timer_id = GLib.timeout_add(130, self.tick)
        GLib.idle_add(self.focus_entry)

    def exercise_metric(self, parent, title, value, highlight=False):
        """Compteur compact adapté aux séances de frappe."""
        block = make_box(gap=4, css='exercise-metric')
        parent.append(block)
        block.append(widget_label(title, 'small-stat'))
        label = widget_label(value, 'exercise-metric-value')
        if highlight:
            label.add_css_class('exercise-metric-timer')
        block.append(label)
        return label

    def focus_entry(self):
        if not self.finished:
            self.text_view.grab_focus()
        return False

    def inline_stat(self, parent, title, value):
        box = self.panel(parent, 'stat-card', 5)
        box.set_hexpand(True)
        box.append(widget_label(title, 'small-stat'))
        lab = widget_label(value, 'stat-medium')
        box.append(lab)
        return lab

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (Gdk.KEY_v, Gdk.KEY_V):
            self.feedback.set_text('Tape toi-même le texte pour gagner des points.')
            return True
        if keyval == Gdk.KEY_BackSpace:
            self.audio.play('key_backspace')
        if keyval == Gdk.KEY_Escape:
            self.home()
            return True
        if self.show_keys and self.motion:
            codepoint = Gdk.keyval_to_unicode(keyval)
            pressed = ('RETOUR' if keyval == Gdk.KEY_BackSpace else
                       chr(codepoint).lower() if codepoint and codepoint >= 32 else '')
            if pressed == ' ':
                pressed = 'ESPACE'
            if self.key_pressed_timeout is not None:
                GLib.source_remove(self.key_pressed_timeout)
                self.key_pressed_timeout = None
            if self.last_pressed_key is not None:
                self.last_pressed_key.remove_css_class('key-pressed')
                self.last_pressed_key = None
            for char, key in self.key_labels:
                if char == pressed:
                    key.add_css_class('key-pressed')
                    self.last_pressed_key = key
                    self.key_pressed_timeout = GLib.timeout_add(120, self.clear_key_flash, key)
                    break
        return False

    def clear_key_flash(self, key):
        key.remove_css_class('key-pressed')
        if self.last_pressed_key is key:
            self.last_pressed_key = None
        self.key_pressed_timeout = None
        return False

    def on_insert(self, buffer, position, text, _byte_len):
        # GTK's insert-text handler runs before the default buffer insertion.
        # Blocking here also catches Shift+Insert, context-menu paste and DnD.
        if self.finished:
            buffer.stop_emission_by_name('insert-text')
            return
        if self.sprint and self.started is not None and self.elapsed() >= 60:
            buffer.stop_emission_by_name('insert-text')
            GLib.idle_add(self.finish)
            return
        expected = self.prompts[self.stage]
        if (len(text) != 1 or text in ('\n', '\r') or
                len(self.current_input()) >= len(expected)):
            buffer.stop_emission_by_name('insert-text')
            self.feedback.set_text('Collage désactivé. Saisis un caractère à la fois.')
            return
        if self.started is None:
            self.started = time.monotonic()
        offset = position.get_offset()
        self.attempts += 1
        if offset >= len(expected) or not same_character(text, expected[offset]):
            self.errors += 1
            self.audio.play('key_error')
        else:
            self.audio.play('key_press')

    def current_input(self):
        return self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)

    def on_changed(self, _buffer):
        if self.finished:
            return
        entered = self.current_input()
        target = self.prompts[self.stage]
        self.target_label.set_markup(rich_target(target, entered))
        if not self.sprint:
            progress = (self.stage + min(len(entered), len(target)) / max(1, len(target))) / len(self.prompts)
            self.bar.set_fraction(min(1.0, progress))
        matches = sum(1 for a, b in zip(entered, target) if same_character(a, b))
        self.current_length = matches
        if matches_target(target, entered):
            # Queue at most one transition, tied to the active exercise token.
            if not self.pending_transition:
                self.pending_transition = True
                GLib.idle_add(self.next_step, self.stage, self.exercise_token)
        elif len(entered) > len(target) or any(not same_character(a, b) for a, b in zip(entered, target)):
            self.feedback.set_text('Une erreur ? Corrige les caractères rouges avec Retour arrière.')
        elif entered:
            self.feedback.set_text('Très bien, continue !')
        else:
            self.feedback.set_text('Le chrono démarre dès la première lettre.')
        self.update_keys(next_expected(target, entered))
        self.update_live()

    def update_prompt(self):
        if self.finished:
            return
        prompt = self.prompts[self.stage]
        self.stage_label.set_text(f'{self.stage + 1} / {len(self.prompts)} mots' if self.sprint else
                                  f'Exercice {self.stage + 1} sur {len(self.prompts)}')
        self.bar.set_fraction(0.0 if self.sprint else self.stage / len(self.prompts))
        self.target_label.set_markup(rich_target(prompt, ''))
        self.update_keys(prompt[0] if prompt else '')
        self.buffer.set_text('')

    def update_keys(self, wanted):
        if not self.show_keys:
            return
        token = wanted.lower()
        if token == '’':
            token = "'"
        if token == ' ':
            token = 'ESPACE'
        if token not in {k for k, _ in self.key_labels}:
            token = ''
        for char, key in self.key_labels:
            if char == token:
                key.add_css_class('key-next')
            else:
                key.remove_css_class('key-next')
        if token == "'":
            message = "Prochaine touche : ’ — apostrophe, touche 4 (sans Maj)"
        elif token == 'ESPACE':
            message = 'Prochaine touche : Espace'
        elif token:
            message = f'Prochaine touche : {wanted}'
        else:
            message = 'Continue à taper avec précision.'
        self.keys_hint.set_text(message)

    def elapsed(self):
        return max(0.0, time.monotonic() - self.started) if self.started else 0.0

    def update_live(self):
        elapsed = self.elapsed()
        total = self.completed_chars + self.current_length
        goal = 100 if self.sprint else self.lesson.target_cpm
        metrics = compute_metrics(total, self.attempts, self.errors, elapsed, goal)
        self.live_accuracy.set_text(f'{metrics["accuracy"]:.0f} %')
        self.live_speed.set_text(str(metrics['cpm']))
        self.live_score.set_text(str(metrics['score']))

    def tick(self):
        if self.finished:
            self.timer_id = None
            return False
        elapsed = self.elapsed()
        if self.sprint:
            left = max(0, 60 - elapsed)
            self.clock_label.set_text(f'{int(left // 60):02d}:{int(left % 60):02d}')
            self.bar.set_fraction(min(1.0, elapsed / 60))
            if self.started and elapsed >= 60:
                self.finish()
                return False
        else:
            self.clock_label.set_text(f'{int(elapsed // 60):02d}:{int(elapsed % 60):02d}')
        self.update_live()
        return True

    def next_step(self, expected_stage, expected_token):
        if expected_token != self.exercise_token or self.finished:
            return False
        self.pending_transition = False
        if (self.stage != expected_stage or
                not matches_target(self.prompts[self.stage], self.current_input())):
            return False
        self.audio.play('word_complete')
        self.completed_chars += len(self.prompts[self.stage])
        self.completed_words += 1
        if self.sprint and self.elapsed() >= 60:
            self.finish()
            return False
        self.stage += 1
        if self.stage >= len(self.prompts):
            self.finish()
        else:
            self.update_prompt()
            self.feedback.set_text('Bravo ! Passe au prochain exercice.')
            self.text_view.grab_focus()
        return False

    @storage_guard
    def finish(self):
        if self.finished:
            return
        duration = min(self.elapsed(), 60.0) if self.sprint else self.elapsed()
        typed = self.completed_chars + (self.current_length if self.sprint else 0)
        if not self.sprint:
            typed = self.completed_chars
        goal = 100 if self.sprint else self.lesson.target_cpm
        metrics = compute_metrics(typed, self.attempts, self.errors, duration, goal)
        lesson = self.lesson
        sprint = self.sprint
        words = self.completed_words
        before = self.db.summary()
        old_level = level_from_xp(before['xp'])
        old_streak = consecutive_days(self.db.active_days())
        old_best = self.db.best(lesson.id)['best_score'] if not sprint else max(
            [r['best_score'] for r in self.db.records() if r['mode'] == 'Sprint'] or [0])
        previous_completed = len(self.db.completed_ids())
        saved = False
        if typed:
            try:
                self.db.save(None if sprint else lesson.id, 'Sprint' if sprint else lesson.kind,
                             typed, self.attempts, self.errors, duration, metrics)
                saved = True
            except (StorageError, ValueError) as exc:
                LOGGER.error('Progression non enregistrée : %s', exc)
        if saved:
            self.audio.play('timer_end' if sprint else 'lesson_complete')
            if metrics['score'] > (old_best or 0) and old_best:
                self.audio.play('new_record')
            if level_from_xp(before['xp'] + metrics['xp']) > old_level:
                self.audio.play('level_up')
            elif metrics['xp'] > 0:
                self.audio.play('xp_gain')
            if consecutive_days(self.db.active_days()) > old_streak:
                self.audio.play('streak_gain')
            if (not sprint and previous_completed < len(self.db.completed_ids())
                    and len(self.db.completed_ids()) in (1, 13, 18, 36)):
                self.audio.play('badge_unlock')
        self.new_page()
        if typed and not saved:
            self.page.append(widget_label('Attention : cette session n’a PAS été enregistrée. '
                                          'Vérifie les droits d’accès et l’espace disque.',
                                          'notice', True))
        banner = self.panel(css='result-card', gap=12)
        banner.append(widget_label('TEMPS ÉCOULÉ' if sprint else 'LEÇON TERMINÉE', 'eyebrow'))
        banner.append(widget_label('Bien joué !', 'hero-title'))
        banner.append(widget_label(f'{words} mots terminés en 60 secondes.' if sprint else
                                   f'Tu as terminé « {lesson.title} ».', 'subtitle', True))
        banner.append(widget_label(f'{metrics["stars"]} / 3 étoiles', 'stars'))
        row = make_box(False, 12)
        self.page.append(row)
        self.inline_stat(row, 'POINTS', str(metrics['score']))
        self.inline_stat(row, 'EXPÉRIENCE', f'+{metrics["xp"]} XP')
        self.inline_stat(row, 'PRÉCISION', f'{metrics["accuracy"]:.0f} %')
        self.inline_stat(row, 'VITESSE', f'{metrics["cpm"]} car/min')
        self.page.append(widget_label(f'Temps : {duration:.1f} secondes  ·  '
                                      f'Erreurs : {self.errors}', 'subtitle'))
        actions = make_box(False, 10)
        self.page.append(actions)
        if not sprint and lesson.id < len(LESSONS) and self.db.unlocked_id() > lesson.id:
            add_button(actions, 'Niveau suivant',
                       lambda i=lesson.id: self.start_lesson(LESSONS[i]), 'primary')
        add_button(actions, 'Recommencer', self.start_sprint if sprint else
                   lambda l=lesson: self.start_lesson(l), 'secondary')
        add_button(actions, 'Retour au parcours', self.home, 'secondary')

    def terminal_panel(self, title, subtitle=''):
        """Terminal GTK4 accessible : décorations non interactives, contenu réel."""
        shell = make_box(gap=0, css='terminal-shell')
        shell.set_hexpand(True)
        self.page.append(shell)
        toolbar = make_box(False, 9, css='terminal-toolbar')
        shell.append(toolbar)
        dots = make_box(False, 6)
        toolbar.append(dots)
        for color in ('terminal-dot-red', 'terminal-dot-amber', 'terminal-dot-green'):
            dot = Gtk.Box()
            dot.add_css_class('terminal-dot')
            dot.add_css_class(color)
            dot.set_size_request(11, 11)
            dots.append(dot)
        name = widget_label(title, 'terminal-toolbar-name')
        name.set_hexpand(True)
        name.set_xalign(0.5)
        toolbar.append(name)
        toolbar.append(widget_label('●', 'terminal-online'))
        body = make_box(gap=18, css='terminal-body')
        shell.append(body)
        prompt = make_box(False, 4, css='terminal-prompt')
        body.append(prompt)
        prompt.append(widget_label('clavia@local', 'terminal-user'))
        prompt.append(widget_label(':~/statistiques', 'terminal-location'))
        prompt.append(widget_label('$', 'terminal-dollar'))
        prompt.append(widget_label(subtitle, 'terminal-command'))
        return body

    def terminal_metric(self, parent, label, value, accent=False):
        block = make_box(gap=5, css='terminal-metric')
        block.set_hexpand(True)
        if parent is not None:
            parent.append(block)
        block.append(widget_label(label, 'terminal-metric-label'))
        block.append(widget_label(str(value), 'terminal-metric-value-accent' if accent else 'terminal-metric-value'))
        return block

    @storage_guard
    def stats(self):
        self.new_page()
        self.page_title('Mes statistiques', 'Une vue claire de ta progression, stockée uniquement sur cet ordinateur.')
        summary = self.db.summary()
        streak = consecutive_days(self.db.active_days())
        acc = round(100 * max(0, summary['attempts'] - summary['errors']) /
                    max(1, summary['attempts']))
        speed = round(summary['chars'] * 60 / max(1.0, summary['seconds']))
        terminal = self.terminal_panel('clavia — statistiques', 'afficher --progression')
        terminal.append(widget_label('RÉSUMÉ DE SESSION', 'terminal-section'))
        grid = Gtk.Grid(column_spacing=0, row_spacing=0)
        grid.set_column_homogeneous(True)
        terminal.append(grid)
        overview = (
            ('XP GAGNÉS', summary['xp'], True),
            ('POINTS', summary['score'], False),
            ('JOURS DE SUITE', f'{streak} jours', True),
            ('EXERCICES', summary['sessions'], False),
            ('PRÉCISION', f'{acc} %', False),
            ('VITESSE MOYENNE', f'{speed} car/min', True),
            ('CARACTÈRES', summary['chars'], False),
            ('ERREURS', summary['errors'], False),
        )
        for i, (name, value, accented) in enumerate(overview):
            grid.attach(self.terminal_metric(None, name, value, accented), i % 2, i // 2, 1, 1)
        terminal.append(widget_label('ÉVOLUTION · 20 DERNIERS EXERCICES', 'terminal-section'))
        recent = self.db.recent_sessions(20)
        if recent:
            terminal.append(SpeedGraph(recent, dark=self.dark))
            terminal.append(widget_label('Vitesse en caractères/minute • 1 point = 1 exercice', 'terminal-hint'))
        else:
            terminal.append(widget_label('Aucune donnée. Termine un exercice pour afficher la courbe.', 'terminal-hint'))
        terminal.append(widget_label('RECORDS PERSONNELS', 'terminal-section'))
        records = self.db.records()
        if not records:
            terminal.append(widget_label('Aucun record enregistré pour le moment.', 'terminal-hint'))
        for record in records:
            line = make_box(False, 12, css='terminal-record')
            terminal.append(line)
            label = widget_label(record['mode'], 'terminal-record-name')
            label.set_hexpand(True)
            line.append(label)
            line.append(widget_label(f'{record["best_cpm"]} car/min', 'terminal-record-value'))
            line.append(widget_label(f'{record["best_score"]} pts', 'terminal-hint'))
        terminal.append(widget_label('BADGES ET OBJECTIFS', 'terminal-section'))
        complete = self.db.completed_ids()
        badges = (
            ('Première leçon', len(complete) > 0),
            ('100 caractères', summary['chars'] >= 100),
            ('Premier texte', any(i >= 13 for i in complete)),
            ('Trois jours de suite', streak >= 3),
            ('200 car/min', any(row['best_cpm'] >= 200 for row in records)),
            ('Parcours terminé', len(complete) == len(LESSONS)),
        )
        for name, unlocked in badges:
            line = make_box(False, 10, css='terminal-record')
            terminal.append(line)
            line.append(widget_label('[OK]' if unlocked else '[--]',
                                     'terminal-user' if unlocked else 'terminal-hint'))
            line.append(widget_label(name, 'terminal-record-name'))
        add_button(self.page, 'Retour au parcours', self.home, 'primary')

    def settings(self):
        self.new_page()
        self.page_title('Paramètres', 'Adapte le jeu à ton confort de lecture et de frappe.')
        panel = self.panel()
        panel.append(widget_label('APPARENCE · JOUR / NUIT', 'eyebrow'))
        theme_line = make_box(False, 12, css='setting-line')
        panel.append(theme_line)
        theme_lbl = widget_label('Thème sombre / clair', 'body-text')
        theme_lbl.set_hexpand(True)
        theme_line.append(theme_lbl)
        theme_line.append(ThemeSwitch(self.dark, self.change_theme))
        prefs = (
            ('Texte plus grand', 'large', self.large),
            ('Afficher le clavier', 'keyboard', self.show_keys),
            ('Animations discrètes', 'motion', self.motion),
            ('Police OpenDyslexic', 'dyslexic', self.dyslexic),
        )
        for name, prop, enabled in prefs:
            line = make_box(False, 12, css='setting-line')
            panel.append(line)
            lbl = widget_label(name, 'body-text')
            lbl.set_hexpand(True)
            line.append(lbl)
            toggle = Gtk.Switch()
            toggle.set_active(enabled)
            toggle.set_valign(Gtk.Align.CENTER)
            if prop == 'dyslexic' and not self.dyslexic_available:
                toggle.set_sensitive(False)
                lbl.set_text(name + ' (non installée)')
            toggle.connect('notify::active', self.change_setting, prop)
            line.append(toggle)
        panel.append(widget_label('SONS', 'eyebrow'))
        for name, prop, value in (
            ('Activer les sons', 'sounds', self.audio.enabled),
            ('Sons de frappe', 'keyboard_sounds', self.audio.keyboard),
            ('Sons de récompense', 'reward_sounds', self.audio.rewards),
        ):
            line = make_box(False, 12, css='setting-line')
            panel.append(line)
            label = widget_label(name, 'body-text')
            label.set_hexpand(True)
            line.append(label)
            switch = Gtk.Switch()
            switch.set_active(value)
            switch.set_valign(Gtk.Align.CENTER)
            switch.connect('notify::active', self.change_setting, prop)
            line.append(switch)
        # Curseur de volume vertical inspiré d'Uiverse, implémenté avec GTK4.
        # La plage reste de 0 à 100 % et la préférence SQLite ne change pas.
        volume_line = make_box(False, 20, css='setting-line')
        panel.append(volume_line)
        volume_details = make_box(True, 5)
        volume_details.set_hexpand(True)
        volume_details.set_valign(Gtk.Align.CENTER)
        volume_details.append(widget_label('Volume général', 'body-text'))
        volume_details.append(widget_label('Glisse vers le haut pour augmenter le son.', 'subtitle', True))
        volume_line.append(volume_details)

        volume_control = make_box(True, 7, css='volume-control')
        volume_control.set_halign(Gtk.Align.CENTER)
        volume_line.append(volume_control)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
        scale.add_css_class('clavia-volume-slider')
        scale.set_size_request(42, 132)
        scale.set_inverted(False)  # 100 % en haut, 0 % en bas
        scale.set_digits(0)
        scale.set_draw_value(False)
        scale.set_value(self.audio.volume)
        scale.set_tooltip_text('Volume sonore, de 0 à 100 %')
        volume_control.append(scale)
        icon = Gtk.Image.new_from_icon_name('audio-volume-high-symbolic')
        icon.add_css_class('volume-icon')
        volume_control.append(icon)
        number = widget_label(f'{self.audio.volume} %', 'volume-percentage')
        volume_control.append(number)
        scale.connect('value-changed', self.change_volume)
        scale.connect('value-changed', lambda widget: number.set_text(f'{round(widget.get_value())} %'))
        if not self.dyslexic_available:
            panel.append(widget_label('Pour utiliser OpenDyslexic, installe la police sur ton système puis relance Clavia.', 'notice', True))
        panel.append(widget_label('La progression est sauvegardée dans '
                                  '~/.local/share/jeu-clavier/progress.db', 'subtitle', True))
        add_button(self.page, 'Retour au parcours', self.home, 'primary')

    def change_volume(self, scale):
        value = round(scale.get_value())
        self.audio.volume = value
        try:
            self.db.set_preference('sound_volume', str(value))
        except StorageError as exc:
            self.show_storage_error('volume', exc)

    def change_setting(self, switch, _pspec, prop):
        val = switch.get_active()
        if prop in ('sounds', 'keyboard_sounds', 'reward_sounds'):
            setattr(self.audio, {'sounds': 'enabled', 'keyboard_sounds': 'keyboard',
                                 'reward_sounds': 'rewards'}[prop], val)
        else:
            setattr(self, {'keyboard': 'show_keys'}.get(prop, prop), val)
        try:
            self.db.set_preference(prop, '1' if val else '0')
        except StorageError as exc:
            self.show_storage_error('paramètre', exc)
        if prop in ('large', 'dyslexic'):
            self.apply_theme()

    def do_shutdown(self):
        self.stop_timers()
        try:
            self.audio.close()
        finally:
            try:
                self.db.close()
            except StorageError as exc:
                LOGGER.error('Fermeture SQLite : %s', exc)
            Gtk.Application.do_shutdown(self)


def main():
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(name)s: %(message)s')
    try:
        app = Clavia()
    except StorageError as exc:
        LOGGER.error('Démarrage de Clavia impossible : %s', exc)
        print('Clavia : impossible d’ouvrir les sauvegardes. Vérifie les permissions et le disque.',
              file=sys.stderr)
        return 1
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
