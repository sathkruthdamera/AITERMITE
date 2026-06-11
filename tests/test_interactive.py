import io

from aitermite.extract import Candidate
from aitermite.interactive import select_command


def _keys(*seq):
    it = iter(seq)

    def reader():
        return next(it)

    return reader


def _cands():
    return [
        Candidate("ls -la", "low", True),
        Candidate("du -sh *", "low", True),
    ]


def test_enter_selects_first():
    chosen = select_command(_cands(), color=False, out=io.StringIO(), key_reader=_keys("enter"))
    assert chosen.command == "ls -la"


def test_down_then_enter_selects_second():
    chosen = select_command(_cands(), color=False, out=io.StringIO(), key_reader=_keys("down", "enter"))
    assert chosen.command == "du -sh *"


def test_wraps_around_with_up():
    chosen = select_command(_cands(), color=False, out=io.StringIO(), key_reader=_keys("up", "enter"))
    assert chosen.command == "du -sh *"


def test_digit_jump_selects():
    chosen = select_command(_cands(), color=False, out=io.StringIO(), key_reader=_keys("2"))
    assert chosen.command == "du -sh *"


def test_cancel_returns_none():
    assert select_command(_cands(), color=False, out=io.StringIO(), key_reader=_keys("q")) is None


def test_dangerous_selection_is_blocked():
    cands = [Candidate("rm -rf /", "dangerous", False)]
    assert select_command(cands, color=False, out=io.StringIO(), key_reader=_keys("enter")) is None
