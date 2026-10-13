"""Acoustic Messenger - send text between phones using sound waves.

Black themed Kivy app with a custom background image, a username screen that
must be completed first, and a text-color picker.
"""
import os

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup, get_color_from_hex, platform

from audio import MAX_PAYLOAD_BYTES, PROTOCOLS, AcousticLink, pack, payload_size, unpack

HERE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND = os.path.join(HERE, "assets", "background.jpg").replace("\\", "/")

PALETTE = [
    "#FFFFFF", "#FFD60A", "#FF9F0A", "#FF453A", "#FF6EC7",
    "#BF5AF2", "#64D2FF", "#0A84FF", "#30D158", "#A8FF60",
]

KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<LoginScreen,ChatScreen>:
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            source: app.background
            pos: self.pos
            size: self.size
        Color:
            rgba: 0, 0, 0, 0.62
        Rectangle:
            pos: self.pos
            size: self.size

<FlatButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    canvas.before:
        Color:
            rgba: (0.04, 0.52, 1, 1) if self.state == 'normal' else (0.02, 0.38, 0.8, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(22)]

<DarkInput@TextInput>:
    multiline: False
    background_normal: ''
    background_active: ''
    background_color: 0, 0, 0, 0
    foreground_color: 1, 1, 1, 1
    hint_text_color: 0.6, 0.62, 0.68, 1
    cursor_color: 1, 1, 1, 1
    padding: dp(16), dp(13)
    write_tab: False
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.75
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(22)]

<LoginScreen>:
    name: 'login'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(28)
        spacing: dp(14)
        Widget:
        Label:
            text: 'Acoustic Messenger'
            font_size: sp(28)
            bold: True
            size_hint_y: None
            height: dp(48)
        Label:
            text: 'Choose a username to get started'
            color: 0.75, 0.78, 0.85, 1
            size_hint_y: None
            height: dp(24)
        DarkInput:
            id: name_input
            hint_text: 'Username'
            size_hint_y: None
            height: dp(48)
            on_text_validate: root.submit()
        Label:
            id: err
            text: ''
            color: 1, 0.35, 0.35, 1
            size_hint_y: None
            height: dp(20)
        FlatButton:
            text: 'Continue'
            size_hint_y: None
            height: dp(48)
            on_release: root.submit()
        Widget:

<ChatScreen>:
    name: 'chat'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10), dp(30), dp(10), dp(10)
        spacing: dp(8)
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            spacing: dp(10)
            Label:
                text: root.initial
                bold: True
                font_size: sp(20)
                size_hint_x: None
                width: dp(46)
                canvas.before:
                    Color:
                        rgba: 0.04, 0.52, 1, 1
                    Ellipse:
                        pos: self.x, self.center_y - dp(23)
                        size: dp(46), dp(46)
            BoxLayout:
                orientation: 'vertical'
                Label:
                    text: root.username
                    bold: True
                    font_size: sp(18)
                    halign: 'left'
                    valign: 'bottom'
                    text_size: self.size
                Label:
                    text: root.state_text
                    font_size: sp(12)
                    color: 0.65, 0.7, 0.8, 1
                    halign: 'left'
                    valign: 'top'
                    text_size: self.size
            Spinner:
                id: speed
                text: 'Normal'
                values: ['Normal', 'Fast', 'Fastest']
                size_hint_x: None
                width: dp(92)
                background_normal: ''
                background_down: ''
                background_color: 0, 0, 0, 0.75
                color: 1, 1, 1, 1
            FlatButton:
                text: 'Aa'
                bold: True
                size_hint_x: None
                width: dp(46)
                on_release: root.open_color_picker()
        ScrollView:
            id: scroll
            bar_width: dp(3)
            GridLayout:
                id: log
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                padding: dp(2), dp(4)
        Label:
            text: root.status
            font_size: sp(11)
            color: 0.6, 0.65, 0.75, 1
            size_hint_y: None
            height: dp(18)
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            DarkInput:
                id: msg
                hint_text: 'Type a message'
                on_text_validate: root.send()
            FlatButton:
                text: 'Send'
                size_hint_x: None
                width: dp(76)
                on_release: root.send()
"""


class Bubble(Label):
    """A rounded dark message bubble."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.markup = True
        self.halign = "left"
        self.padding = (dp(12), dp(8))
        self.text_size = (Window.width * 0.7, None)
        self.bind(texture_size=self._resize, pos=self._redraw, size=self._redraw)
        with self.canvas.before:
            self._color = Color(0, 0, 0, 0.72)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])

    def _resize(self, *_):
        self.size = (self.texture_size[0] + dp(24), self.texture_size[1] + dp(16))

    def _redraw(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class LoginScreen(Screen):
    def on_pre_enter(self, *args):
        saved = App.get_running_app().saved_username
        if saved and not self.ids.name_input.text:
            self.ids.name_input.text = saved

    def submit(self):
        name = self.ids.name_input.text.strip().replace("|", "")
        if len(name) < 2:
            self.ids.err.text = "Username must be at least 2 characters"
            return
        if len(name) > 20:
            self.ids.err.text = "Username must be 20 characters or fewer"
            return
        self.ids.err.text = ""
        App.get_running_app().login(name)


class ChatScreen(Screen):
    username = StringProperty("")
    initial = StringProperty("?")
    state_text = StringProperty("Online")
    status = StringProperty("Status: Starting...")
    text_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bubbles = []

    def set_user(self, name):
        self.username = name
        self.initial = name[:1].upper()

    def apply_color(self, rgba):
        self.text_color = list(rgba)
        for bubble in self._bubbles:
            bubble.color = self.text_color

    def add_message(self, name, text, mine):
        bubble = Bubble(
            text="[size=12][color=9aa4b5]%s[/color][/size]\n%s"
            % (escape_markup("You" if mine else name), escape_markup(text)),
            color=self.text_color,
        )
        row = BoxLayout(size_hint_y=None, height=bubble.height)
        bubble.bind(height=lambda _inst, h: setattr(row, "height", h))
        if mine:
            row.add_widget(Widget())
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Widget())
        self._bubbles.append(bubble)
        self.ids.log.add_widget(row)
        Clock.schedule_once(lambda _dt: setattr(self.ids.scroll, "scroll_y", 0), 0.1)

    def send(self):
        text = self.ids.msg.text.strip()
        if not text:
            return
        size = payload_size(self.username, text)
        if size > MAX_PAYLOAD_BYTES:
            self.status = "Status: Message too long (%d/%d bytes)" % (size, MAX_PAYLOAD_BYTES)
            return
        App.get_running_app().send_text(text, self.ids.speed.text)
        self.add_message(self.username, text, True)
        self.ids.msg.text = ""

    def open_color_picker(self):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        grid = GridLayout(cols=5, spacing=dp(8), size_hint_y=None, height=dp(96))
        popup = Popup(
            title="Text color",
            content=content,
            size_hint=(0.9, None),
            height=dp(260),
            background="",
            background_color=(0.04, 0.04, 0.06, 0.96),
            separator_color=(0.04, 0.52, 1, 1),
        )

        def choose(hex_code):
            rgba = get_color_from_hex(hex_code)
            self.apply_color(rgba)
            App.get_running_app().save_color(hex_code)
            popup.dismiss()

        for hex_code in PALETTE:
            swatch = Button(background_normal="", background_color=get_color_from_hex(hex_code))
            swatch.bind(on_release=lambda _b, h=hex_code: choose(h))
            grid.add_widget(swatch)
        content.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        hex_input = TextInput(
            hint_text="#RRGGBB", multiline=False, write_tab=False,
            foreground_color=(1, 1, 1, 1), background_color=(0.12, 0.12, 0.16, 1),
            padding=(dp(12), dp(12)),
        )
        apply_btn = Button(text="Apply", size_hint_x=None, width=dp(80))

        def apply_hex(*_):
            value = hex_input.text.strip()
            if not value.startswith("#"):
                value = "#" + value
            if len(value) in (4, 7):
                try:
                    choose(value)
                except Exception:
                    hex_input.text = ""

        apply_btn.bind(on_release=apply_hex)
        hex_input.bind(on_text_validate=apply_hex)
        row.add_widget(hex_input)
        row.add_widget(apply_btn)
        content.add_widget(row)
        popup.open()


class AcousticApp(App):
    title = "Acoustic Messenger"
    background = StringProperty(BACKGROUND)

    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        Builder.load_string(KV)
        self.store = JsonStore(os.path.join(self.user_data_dir, "settings.json"))
        self.saved_username = self.store.get("user")["name"] if self.store.exists("user") else ""
        self.saved_color = self.store.get("color")["hex"] if self.store.exists("color") else "#FFFFFF"

        self.link = AcousticLink(self._on_payload, self._on_state)
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))
        self.login_screen = LoginScreen()
        self.chat_screen = ChatScreen()
        self.chat_screen.apply_color(get_color_from_hex(self.saved_color))
        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.chat_screen)
        return self.sm

    # ---------------------------------------------------------------- session
    def login(self, name):
        self.store.put("user", name=name)
        self.chat_screen.set_user(name)
        self.sm.current = "chat"
        self._start_audio()

    def save_color(self, hex_code):
        self.store.put("color", hex=hex_code)

    def _start_audio(self):
        if platform == "android":
            from android.permissions import Permission, request_permissions

            def after(_perms, results):
                if results and all(results):
                    self.link.start_listening()
                else:
                    self._on_state("error:microphone permission denied")

            request_permissions([Permission.RECORD_AUDIO], after)
        else:
            self.link.start_listening()

    def on_stop(self):
        self.link.stop_listening()

    # --------------------------------------------------------------- messages
    def send_text(self, text, speed):
        self.link.send(pack(self.chat_screen.username, text), PROTOCOLS.get(speed, 0))

    @mainthread
    def _on_payload(self, payload):
        name, text = unpack(payload)
        self.chat_screen.add_message(name, text, False)
        self.chat_screen.status = "Status: Received from %s" % name

    @mainthread
    def _on_state(self, state):
        chat = self.chat_screen
        if state == "listening":
            chat.status = "Status: Listening..."
        elif state == "sending":
            chat.status = "Status: Sending..."
        elif state == "idle":
            chat.status = "Status: Idle"
        elif state.startswith("error:"):
            chat.status = "Status: " + state[6:]


if __name__ == "__main__":
    AcousticApp().run()
