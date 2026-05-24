from aitermite.precheck import precheck_command


def test_git_command_typo():
    result = precheck_command("gti status")
    assert result.suggestion == "git status"


def test_git_status_typo():
    result = precheck_command("git sttaus")
    assert result.suggestion == "git status"
