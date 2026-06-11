from aitermite.nl_detect import looks_like_thought


def test_question_is_thought():
    assert looks_like_thought("how do i list files by size")
    assert looks_like_thought("what is using port 8080?")
    assert looks_like_thought("show me the largest folders here")


def test_trailing_question_mark_is_thought():
    assert looks_like_thought("largest files?")


def test_real_command_typo_is_not_thought():
    # git resolves on PATH-ish known-command logic; subcommand typo -> fixer.
    assert not looks_like_thought("git sttaus")
    assert not looks_like_thought("gti status")


def test_single_token_is_not_thought():
    assert not looks_like_thought("lss")
    assert not looks_like_thought("docker")


def test_path_or_assignment_is_not_thought():
    assert not looks_like_thought("./build.sh now please")
    assert not looks_like_thought("FOO=bar run the thing")


def test_flagged_command_line_is_not_thought():
    assert not looks_like_thought("find . -name '*.py'")
