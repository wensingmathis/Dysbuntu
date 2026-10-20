#!/usr/bin/env python3
"""Clavia : jeu de frappe AZERTY natif pour Linux (GTK 4)."""
import math
import random
import subprocess
import sys
import time
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, GLib, Gtk, Pango

from content import LESSONS, SPRINT_WORDS
from engine import compute_metrics, consecutive_days, level_from_xp, next_expected, rich_target
from storage import Storage

BASE = Path(__file__).resolve().parent.parent
CSS_FILE = BASE / 'assets' / 'style.css'
ROWS = (
    ('²', '&', 'é', '"', "'", '(', '-', 'è', '_', 'ç', 'à', ')', '='),
    ('a', 'z', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '^', '$'),
    ('q', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'ù', '*'),
    ('<', 'w', 'x', 'c', 'v', 'b', 'n', ',', ';', ':', '!'),
    ('ESPACE',),
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
    b = Gtk.Button(label=label)
    b.add_css_class(css)
    b.connect('clicked', lambda *_: callback())
    if expand:
        b.set_hexpand(True)
    parent.append(b)
    return b


def clear(box):
    while box.get_first_child() is not None:
        box.remove(box.get_first_child())


class Flame(Gtk.DrawingArea):
    """Pictogramme de série quotidienne : une flamme vectorielle 2D mate."""

    def __init__(self):
        super().__init__()
        self.set_content_width(30)
        self.set_content_height(34)
        self.set_draw_func(self.draw_flame)

    def draw_flame(self, _area, cr, width, height):
        cr.save()
        cr.translate(width / 2, height / 2)
        cr.scale(min(width / 34, height / 40), min(width / 34, height / 40))
        cr.translate(-17, -20)
        cr.move_to(17, 2)
        cr.curve_to(19, 9, 28, 13, 29, 23)
        cr.curve_to(30, 31, 25, 38, 17, 38)
        cr.curve_to(7, 38, 3, 32, 5, 24)
        cr.curve_to(7, 19, 12, 15, 12, 9)
        cr.curve_to(16, 13, 17, 8, 17, 2)
        cr.close_path()
        cr.set_source_rgb(226 / 255, 183 / 255, 20 / 255)
        cr.fill()
        cr.restore()


class SpeedGraph(Gtk.DrawingArea):
    """Courbe minimaliste des vitesses enregistrées, sans dépendance externe."""

    def __init__(self, sessions):
        super().__init__()
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
            cr.set_source_rgb(0.22, 0.22, 0.24)
            cr.set_line_width(1)
            cr.move_to(left, y)
            cr.line_to(right, y)
            cr.stroke()
        points = []
        for i, value in enumerate(self.speeds):
            x = left + (right - left) * i / max(1, len(self.speeds) - 1)
            y = bottom - chart_height * (value - min_speed) / max_speed
            points.append((x, y))
        cr.set_source_rgb(226 / 255, 183 / 255, 20 / 255)
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
        self.motion = self.db.preference('motion', '1') == '1'
        self.show_keys = self.db.preference('keyboard', '1') == '1'
        self.dyslexic = self.db.preference('dyslexic', '0') == '1'
        self.dyslexic_available = self.check_font()
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
            gtk_settings.set_property('gtk-application-prefer-dark-theme', True)
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

    def apply_theme(self):
        """Une seule palette Dark Slate ; les polices d'accessibilité restent actives."""
        if hasattr(self, 'provider'):
            Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), self.provider)
        raw = CSS_FILE.read_text(encoding='utf-8')
        self.provider = Gtk.CssProvider()
        self.provider.load_from_string(raw)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        if hasattr(self, 'window'):
            for widget in (self.window,):
                if self.large:
                    widget.add_css_class('large-text')
                else:
                    widget.remove_css_class('large-text')
                if self.dyslexic and self.dyslexic_available:
                    widget.add_css_class('dyslexic-font')
                else:
                    widget.remove_css_class('dyslexic-font')


    def stop_timers(self):
        for field in ('timer_id', 'flame_id', 'key_pressed_timeout'):
            timer = getattr(self, field)
            if timer is not None:
                GLib.source_remove(timer)
                setattr(self, field, None)

    def new_page(self):
        self.stop_timers()
        self.finished = True
        clear(self.page)
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
        next_lesson = LESSONS[min(unlocked, 18) - 1]
        add_button(actions, f'Continuer : niveau {next_lesson.id}',
                   lambda l=next_lesson: self.start_lesson(l), 'primary')
        add_button(actions, 'Sprint de 60 secondes', self.start_sprint, 'secondary')

        statsrow = make_box(False, 12)
        self.page.append(statsrow)
        self.stat_card(statsrow, 'NIVEAU', str(lvl), f'{summ["xp"]} XP au total')
        self.stat_card(statsrow, 'JOURS DE SUITE', str(streak),
                       'Entraînement régulier', flame=True)
        self.stat_card(statsrow, 'LEÇONS VALIDÉES', str(min(unlocked - 1, 18)) + ' / 18',
                       'Du mot au texte')
        self.stat_card(statsrow, 'OBJECTIF DU JOUR', f'{min(3, self.db.today_sessions())} / 3',
                       '3 exercices par jour')

        self.page.append(widget_label('Ton parcours', 'section-title'))
        self.page.append(widget_label('Termine une leçon pour débloquer la suivante. '
                                      'Tu peux refaire tes leçons pour améliorer ton record.', 'subtitle', True))
        completed = self.db.completed_ids()
        for kind in ('Mots', 'Phrases', 'Textes'):
            section = self.panel(gap=13)
            heading = make_box(False, 10)
            section.append(heading)
            heading.append(widget_label(kind.upper(), 'chapter'))
            heading.append(widget_label({'Mots': '01', 'Phrases': '02', 'Textes': '03'}[kind], 'chapter-number'))
            for lesson in LESSONS:
                if lesson.kind != kind:
                    continue
                available = lesson.id <= unlocked
                best = self.db.best(lesson.id)
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
        item = self.panel(parent, 'stat-card', 6)
        item.set_hexpand(True)
        item.append(widget_label(heading, 'small-stat'))
        value_row = make_box(False, 6)
        item.append(value_row)
        if flame:
            self.flame = Flame()
            value_row.append(self.flame)
        value_row.append(widget_label(value, 'big-stat'))
        item.append(widget_label(foot, 'muted', True))

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
        add_button(top, 'Quitter', self.home, 'nav')

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
            board = make_box(gap=5)
            keyboard_panel.append(board)
            for row in ROWS:
                line = make_box(False, 5)
                line.set_halign(Gtk.Align.CENTER)
                board.append(line)
                for char in row:
                    key = widget_label(char, 'keycap')
                    key.set_size_request(215 if char == 'ESPACE' else 43, 36)
                    line.append(key)
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
        if keyval == Gdk.KEY_Escape:
            self.home()
            return True
        if self.show_keys and self.motion:
            codepoint = Gdk.keyval_to_unicode(keyval)
            if codepoint and codepoint >= 32:
                pressed = chr(codepoint).lower()
                pressed = 'ESPACE' if pressed == ' ' else pressed
                for char, key in self.key_labels:
                    key.remove_css_class('key-pressed')
                    if char == pressed:
                        key.add_css_class('key-pressed')
                        if self.key_pressed_timeout:
                            GLib.source_remove(self.key_pressed_timeout)
                        self.key_pressed_timeout = GLib.timeout_add(120, self.clear_key_flash, key)
                        break
        return False

    def clear_key_flash(self, key):
        key.remove_css_class('key-pressed')
        self.key_pressed_timeout = None
        return False

    def on_insert(self, _buffer, position, text, _byte_len):
        if self.finished:
            return
        if not self.started:
            self.started = time.monotonic()
        expected = self.prompts[self.stage]
        offset = position.get_offset()
        for index, char in enumerate(text):
            if char in ('\n', '\r'):
                continue
            self.attempts += 1
            if offset + index >= len(expected) or char != expected[offset + index]:
                self.errors += 1

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
        matches = sum(1 for a, b in zip(entered, target) if a == b)
        self.current_length = matches
        if entered == target:
            # GTK ne doit pas vider le TextBuffer depuis le signal « changed ».
            GLib.idle_add(self.next_step, self.stage)
        elif len(entered) > len(target) or any(a != b for a, b in zip(entered, target)):
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
        if token == ' ':
            token = 'ESPACE'
        if token not in {k for k, _ in self.key_labels}:
            token = ''
        for char, key in self.key_labels:
            if char == token:
                key.add_css_class('key-next')
            else:
                key.remove_css_class('key-next')
        self.keys_hint.set_text(f'Prochaine touche : {"Espace" if token == "ESPACE" else token}'
                                 if token else 'Continue à taper avec précision.')

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

    def next_step(self, expected_stage):
        if self.finished or self.stage != expected_stage or self.current_input() != self.prompts[self.stage]:
            return False
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
        if typed:
            self.db.save(None if sprint else lesson.id, 'Sprint' if sprint else lesson.kind,
                         typed, self.attempts, self.errors, duration, metrics)
        self.new_page()
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

    def stats(self):
        self.new_page()
        self.page_title('Mes statistiques', 'Tes résultats sont enregistrés uniquement sur cet ordinateur.')
        summary = self.db.summary()
        streak = consecutive_days(self.db.active_days())
        row = make_box(False, 12)
        self.page.append(row)
        self.inline_stat(row, 'XP GAGNÉS', str(summary['xp']))
        self.inline_stat(row, 'POINTS', str(summary['score']))
        self.inline_stat(row, 'SÉRIE', f'{streak} jours')
        self.inline_stat(row, 'EXERCICES', str(summary['sessions']))
        row2 = make_box(False, 12)
        self.page.append(row2)
        acc = round(100 * max(0, summary['attempts'] - summary['errors']) /
                    max(1, summary['attempts']))
        speed = round(summary['chars'] * 60 / max(1.0, summary['seconds']))
        self.inline_stat(row2, 'PRÉCISION TOTALE', f'{acc} %')
        self.inline_stat(row2, 'VITESSE MOYENNE', f'{speed} car/min')
        self.inline_stat(row2, 'CARACTÈRES ÉCRITS', str(summary['chars']))
        self.inline_stat(row2, 'ERREURS', str(summary['errors']))
        self.page.append(widget_label('Évolution de ta vitesse', 'section-title'))
        recent = self.db.recent_sessions(20)
        if recent:
            chart = self.panel(css='chart-surface', gap=10)
            chart.append(widget_label('20 DERNIERS EXERCICES · CARACTÈRES PAR MINUTE', 'eyebrow'))
            chart.append(SpeedGraph(recent))
            chart.append(widget_label('Chaque point représente un exercice terminé.', 'muted'))
        else:
            self.page.append(widget_label('Le graphique apparaîtra après ton premier exercice.', 'subtitle'))
        self.page.append(widget_label('Tes records par mode', 'section-title'))
        records = self.panel()
        if not self.db.records():
            records.append(widget_label('Termine une leçon pour voir tes premiers records.', 'subtitle'))
        for record in self.db.records():
            line = make_box(False, 10, css='record-line')
            records.append(line)
            text = widget_label(record['mode'], 'lesson-title')
            text.set_hexpand(True)
            line.append(text)
            line.append(widget_label(f'{record["best_cpm"]} car/min', 'mini-accent'))
            line.append(widget_label(f'{record["best_score"]} points', 'subtitle'))

        self.page.append(widget_label('Badges', 'section-title'))
        box = self.panel()
        complete = self.db.completed_ids()
        badges = (
            ('Première leçon', len(complete) > 0),
            ('100 caractères', summary['chars'] >= 100),
            ('Premier texte', any(i >= 13 for i in complete)),
            ('Trois jours de suite', streak >= 3),
            ('200 car/min', any(row['best_cpm'] >= 200 for row in self.db.records())),
            ('Parcours terminé', len(complete) == 18),
        )
        for name, unlocked in badges:
            line = make_box(False, 12, css='badge-line')
            box.append(line)
            line.append(widget_label('ACQUIS' if unlocked else 'À OBTENIR',
                                     'mini-accent' if unlocked else 'muted'))
            line.append(widget_label(name, 'body-text'))
        add_button(self.page, 'Retour au parcours', self.home, 'primary')

    def settings(self):
        self.new_page()
        self.page_title('Paramètres', 'Adapte le jeu à ton confort de lecture et de frappe.')
        panel = self.panel()
        panel.append(widget_label('THÈME DARK SLATE · CONTRASTE SOBRE', 'eyebrow'))
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
        if not self.dyslexic_available:
            panel.append(widget_label('Pour utiliser OpenDyslexic, installe la police sur ton système puis relance Clavia.', 'notice', True))
        panel.append(widget_label('La progression est sauvegardée dans '
                                  '~/.local/share/jeu-clavier/progress.db', 'subtitle', True))
        add_button(self.page, 'Retour au parcours', self.home, 'primary')

    def change_setting(self, switch, _pspec, prop):
        val = switch.get_active()
        setattr(self, {'keyboard': 'show_keys'}.get(prop, prop), val)
        self.db.set_preference(prop, '1' if val else '0')
        if prop in ('large', 'dyslexic'):
            self.apply_theme()

    def do_shutdown(self):
        self.stop_timers()
        self.db.close()
        Gtk.Application.do_shutdown(self)


def main():
    app = Clavia()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
