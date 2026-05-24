from aitermite.redaction import redact


def test_redacts_openai_style_key():
    value = redact("sk-aaaaaaaaaaaaaaaaaaaaaaaa")
    assert "aaaaaaaa" not in value
    assert "REDACTED" in value
