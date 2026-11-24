"""A permissive stand-in for PySide6 so the UI code can be imported and constructed without Qt (catches Python-level mistakes only)."""
import sys
import types


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Any()
    def __or__(cls, o): return Any()
    def __ror__(cls, o): return Any()


class Any(metaclass=_Meta):
    def __init__(self, *a, **k): pass
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Any()
    def __call__(self, *a, **k): return Any()
    def __iter__(self): return iter([])
    def __bool__(self): return False
    def __len__(self): return 0
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __index__(self): return 0
    def __or__(self, o): return Any()
    __ror__ = __and__ = __rand__ = __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __truediv__ = __rtruediv__ = __floordiv__ = __neg__ = __or__
    def __lt__(self, o): return False
    __le__ = __gt__ = __ge__ = __lt__
    def __getitem__(self, i): return Any()
    def __format__(self, spec): return "0"
    def __round__(self, n=None): return 0


def _mod(name):
    m = types.ModuleType(name)
    m.__getattr__ = lambda n: (_ for _ in ()).throw(AttributeError(n)) if n.startswith("__") else type(n, (Any,), {})
    return m


def install():
    names = ["PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvg", "PySide6.QtMultimedia",
             "PySide6.QtSerialPort", "PySide6.QtWebSockets"]
    for n in names:
        sys.modules[n] = _mod(n)
    sys.modules["PySide6.QtCore"].Signal = lambda *a, **k: Any()
    for n in names[1:]:
        setattr(sys.modules["PySide6"], n.split(".")[1], sys.modules[n])
