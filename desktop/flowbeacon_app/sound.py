"""Plays the app sounds. Silent (never crashes) if Qt Multimedia is unavailable."""
from pathlib import Path

from PySide6.QtCore import QUrl

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover
    QMediaPlayer = None

SOUNDS = Path(__file__).parent / "assets" / "sounds"
NAMES = ["click", "connect", "disconnect", "baseline", "rain", "possible", "warning", "risk", "overflow", "predict", "normal"]


class Sound:
    def __init__(self, store):
        self.store, self.pl = store, {}

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

    def play(self, name, idle=False):
        if self.store["mute"]:
            return
        if not self.store["snd"].get(name, True):
            return
        e = self._get(name)
        if not e:
            return
        pl, out = e
        if idle and pl.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        out.setVolume(max(0.0, min(1.0, float(self.store["vol"]))))
        pl.setPosition(0)
        pl.play()
