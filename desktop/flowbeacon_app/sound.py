"""Plays the app sounds. Silent (never crashes) if Qt Multimedia is unavailable."""
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QUrl, Qt

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover
    QMediaPlayer = None

from . import quiet as quiet_hours

SOUNDS = Path(__file__).parent / "assets" / "sounds"
NAMES = ["click", "connect", "disconnect", "baseline", "rain", "possible", "warning", "risk", "overflow", "predict", "normal", "knob_tick", "knob_spin"]
UI = ("click", "connect", "disconnect", "baseline", "normal", "knob_tick", "knob_spin")   # switched by "Interface sounds"


def sound_off(store, name):
    """Same rule as the web app's soundOff(): mute, per-sound switch and quiet hours (overflow and risk always play)."""
    if store["mute"]:
        return True
    key = "ui" if name in UI else name
    if store["snd"].get(key, True) is False:
        return True
    return quiet_hours.in_quiet(store["quiet"]) and name not in ("overflow", "risk")


class Sound:
    def __init__(self, store):
        self.store, self.pl = store, {}
        self._tick_at = 0.0

    def _get(self, name):
        if QMediaPlayer is None:
            return None
        if name not in self.pl:
            f = next((SOUNDS / (name + e) for e in (".mp3", ".wav") if (SOUNDS / (name + e)).exists()), None)
            if f is None:
                return None
            out = QAudioOutput()
            pl = QMediaPlayer()
            pl.setAudioOutput(out)
            pl.setSource(QUrl.fromLocalFile(str(f)))
            self.pl[name] = (pl, out)
        return self.pl[name]

    def play(self, name, idle=False, rate=1.0, scale=1.0):
        if sound_off(self.store, name):
            return
        e = self._get(name)
        if not e:
            return
        pl, out = e
        if idle and pl.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        out.setVolume(max(0.0, min(1.0, float(self.store["vol"]) * scale)))
        try:
            pl.setPlaybackRate(rate)
        except Exception:  # noqa: BLE001
            pass
        pl.setPosition(0)
        pl.play()

    # ---- dial sounds (same as the web app: a tick per notch, a spin while the dial is held) ----
    def knob_tick(self, f):
        t = time.monotonic()
        if t - self._tick_at < 0.038:
            return
        self._tick_at = t
        self.play("knob_tick", rate=0.92 + f * 0.2, scale=0.8)

    def knob_spin(self):
        self.play("knob_spin", scale=0.8)

    def knob_stop(self):
        e = self.pl.get("knob_spin")
        if e:
            e[0].pause()


class ClickSounds(QObject):
    """Application-wide filter: every button, switch and segmented-control press plays the click, like the web app."""

    def __init__(self, sound):
        super().__init__()
        self.sound = sound

    def eventFilter(self, obj, ev):  # noqa: N802 - Qt name
        try:
            if ev.type() == QEvent.Type.MouseButtonRelease and ev.button() == Qt.MouseButton.LeftButton:
                from PySide6.QtWidgets import QAbstractButton
                if isinstance(obj, QAbstractButton) and obj.isEnabled() and obj.rect().contains(ev.position().toPoint()):
                    self.sound.play("click")
        except Exception:  # noqa: BLE001 - a sound must never break the UI
            pass
        return False
