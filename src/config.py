import yaml
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def load_config(path: str | None = None) -> dict:
    """Load config.yaml (or a custom path) and return as a plain dict."""
    cfg_path = Path(path) if path else _ROOT / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)
