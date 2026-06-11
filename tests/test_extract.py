from aitermite.extract import candidates, extract_commands


def test_extracts_bash_fenced_block():
    answer = "Try this:\n```bash\nls -la\ndu -sh *\n```\nDone."
    assert extract_commands(answer) == ["ls -la", "du -sh *"]


def test_extracts_powershell_block():
    answer = "Run:\n```powershell\nGet-ChildItem | Sort-Object Length\n```"
    assert extract_commands(answer) == ["Get-ChildItem | Sort-Object Length"]


def test_strips_prompt_prefixes_and_comments():
    answer = "```sh\n$ git status\n# a comment\nPS C:\\> dir\n```"
    assert extract_commands(answer) == ["git status", "dir"]


def test_ignores_non_shell_languages():
    answer = "```python\nprint('hi')\n```\n```json\n{\"a\":1}\n```"
    assert extract_commands(answer) == []


def test_dedupes_preserving_order():
    answer = "```\nls\npwd\nls\n```"
    assert extract_commands(answer) == ["ls", "pwd"]


def test_candidates_block_dangerous():
    cands = candidates("```bash\nrm -rf /\n```")
    assert len(cands) == 1
    assert cands[0].risk == "dangerous"
    assert cands[0].allowed is False


def test_candidates_allow_pipe_as_medium():
    cands = candidates("```bash\ncat file | grep x\n```")
    assert cands[0].allowed is True
    assert cands[0].risk == "medium"
