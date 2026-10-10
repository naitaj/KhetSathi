"""Configuration loader for KhetSathi decision engine.

Loads crops, soils, and safety rule specifications from bundled JSON configs.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent


def load_json(filename: str) -> Dict[str, Any]:
    file_path = CONFIG_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file {filename} not found at {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_crops_config() -> Dict[str, Any]:
    return load_json("crops.json")


def get_soils_config() -> Dict[str, Any]:
    return load_json("soils.json")


def get_safety_config() -> Dict[str, Any]:
    return load_json("safety.json")
