"""Language (English / Tamil) and text size. Qt is imported only inside apply(), so the logic modules stay testable."""
from . import tamil

STATE = {"lang": "en", "zoom": 1.0}
_UP = {k.upper(): k for k in tamil.TA}


def set_lang(lang):
    STATE["lang"] = lang if lang in ("en", "ta") else "en"


def set_zoom(z):
    STATE["zoom"] = float(z) if z else 1.0


def tr(s):
    """Translate any UI string (also upper-case headings)."""
    if STATE["lang"] != "ta" or not isinstance(s, str):
        return s
    if s in tamil.TA:
        return tamil.TA[s]
    if s in _UP:
        return tamil.TA[_UP[s]].upper()
    return tamil.trans(s, "ta")


def tr_ev(s):
    return tamil.trans_ev(s, STATE["lang"])


def _swap(w, get, put):
    cur = get()
    if not isinstance(cur, str) or not cur:
        return
    o, t = w.property("_o"), w.property("_t")
    if o is None or (cur != o and cur != t):
        o = cur                                   # new text set by the app since the last pass
    new = tr(o)
    if new != cur:
        put(new)
    w.setProperty("_o", o)
    w.setProperty("_t", new)


def apply(root):
    """Re-applies the language and the text size to every widget below `root` (the web app's applyLang and zoom)."""
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QLineEdit, QWidget
    from .controls import H2
    z = STATE["zoom"]
    for w in root.findChildren(QWidget):
        if isinstance(w, H2):
            o = w.property("_o")
            if o is None:
                o = w.text
                w.setProperty("_o", o)
            w.text = tr(o)
            w.updateGeometry()
            w.update()
            continue
        if isinstance(w, QLabel):
            _swap(w, w.text, w.setText)
        elif isinstance(w, QAbstractButton):
            _swap(w, w.text, w.setText)
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                o = w.itemData(i, 0x0100 + 7) or w.itemText(i)            # keep the English text in a custom role
                w.setItemData(i, o, 0x0100 + 7)
                w.setItemText(i, tr(o))
        if isinstance(w, (QLabel, QAbstractButton, QLineEdit, QComboBox)):
            base = w.property("_px")
            f = w.font()
            if base is None:
                base = f.pixelSize()
                if base <= 0:
                    continue
                w.setProperty("_px", base)
            f.setPixelSize(max(8, int(round(float(base) * z))))
            w.setFont(f)
