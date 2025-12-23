"""Configuration loader for the pipeline."""

import yaml
from pathlib import Path
from typing import Any

_CONFIG_CACHE: dict | None = None


def get_project_root() -> Path:
    """Get the project root directory."""
    # Walk up from this file to find config.yaml
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config.yaml").exists():
            return parent
    raise FileNotFoundError("Could not find project root (no config.yaml found)")


def load_config(config_path: Path | str | None = None) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses config.yaml in project root.

    Returns:
        Configuration dictionary with paths resolved to absolute paths.
    """
    global _CONFIG_CACHE

    if _CONFIG_CACHE is not None and config_path is None:
        return _CONFIG_CACHE

    root = get_project_root()

    if config_path is None:
        config_path = root / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Resolve paths relative to project root
    paths = config.get("paths", {})
    for key, value in paths.items():
        if isinstance(value, str):
            paths[key] = str(root / value)

    config["paths"] = paths
    config["_root"] = str(root)

    if config_path is None:
        _CONFIG_CACHE = config

    return config


def get_path(config: dict, *keys: str) -> Path:
    """
    Get a path from config, creating parent directories if needed.

    Args:
        config: Configuration dictionary
        keys: Keys to navigate the config dict

    Returns:
        Path object
    """
    value = config
    for key in keys:
        value = value[key]
    return Path(value)


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, creating if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path
