"""Signed producer adapter configuration (M18 item 18.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, load_config
from agentinbox.doctor import Report, render_explain


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_a_producer_key_reference_is_parsed(tmp_path: Path) -> None:
    parsed = load_config(
        write(
            tmp_path,
            """
[classes.irreversible]
ttl_seconds = 300

[producers.agentpolicy]
key_ref = "env:ADAPTER_KEY"
""",
        )
    )
    assert parsed.producers["agentpolicy"].key_ref == "env:ADAPTER_KEY"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('[producers.agentpolicy]\nkey_ref = "literal-secret"\n', "reference"),
        ("[producers.agentpolicy]\n", "required"),
        (
            '[producers.agentpolicy]\nkey_ref = "env:X"\nunknown = 1\n',
            "unknown key",
        ),
    ],
)
def test_invalid_producer_configs_refuse(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, body))


def test_doctor_explains_producers(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
[classes.irreversible]
ttl_seconds = 300

[producers.agentpolicy]
key_ref = "env:ADAPTER_KEY"
""",
    )
    parsed = load_config(path)
    text = render_explain(Report(checks=(), config=parsed), tmp_path, path)

    assert text is not None
    assert "producer agentpolicy: key_ref=env:ADAPTER_KEY" in text
