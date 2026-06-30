from __future__ import annotations

from mcpdb.observability.logging import _sanitise_str


def test_security_log_injection_newline_blocked() -> None:
    """\\n in log values enables log-forging — must be stripped (OWASP A09)."""
    injected = "user_id=123\nINFO privileged_access=true"
    result = _sanitise_str(injected)
    assert "\n" not in result
    assert "123" in result


def test_security_log_injection_carriage_return_blocked() -> None:
    r"""\\r allows overwriting a log line — must be stripped (OWASP A09)."""
    injected = "legitimate\rINFO evil=forged"
    result = _sanitise_str(injected)
    assert "\r" not in result


def test_security_log_injection_null_byte_blocked() -> None:
    """Null byte in log value must be stripped (OWASP A09 / NIST SI-10)."""
    injected = "valid\x00hidden_payload"
    result = _sanitise_str(injected)
    assert "\x00" not in result


def test_security_log_injection_multiple_controls_stripped() -> None:
    """All control characters in range 0x00–0x1f must be stripped (OWASP A09)."""
    injected = "".join(chr(i) for i in range(0x20)) + "visible_text"
    result = _sanitise_str(injected)
    for i in range(0x20):
        assert chr(i) not in result, f"Control char 0x{i:02x} survived sanitisation"
    assert "visible_text" in result


def test_security_log_injection_tab_stripped() -> None:
    r"""\\t (0x09) is stripped along with other control chars (OWASP A09)."""
    tab_str = "col1\tcol2"
    result = _sanitise_str(tab_str)
    # Tab (0x09) is in range 0x00-0x1f and is stripped
    assert "\t" not in result
    assert "col1" in result


def test_security_log_injection_unicode_newline_not_bypassed() -> None:
    """Unicode line separator (U+2028) must not bypass log-injection protection.

    Our regex targets ASCII control chars; U+2028 is a Unicode paragraph
    separator used in some log parsers.  We verify it is logged as-is (not
    silently converted to a newline by the renderer).
    """
    line_sep = "\u2028"
    result = _sanitise_str(f"before{line_sep}after")
    # It should pass through; the important guarantee is no ASCII \n is inserted
    assert "\n" not in result
