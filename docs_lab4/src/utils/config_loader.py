
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config", "config.yaml"
)

def load_config(config_path: str = None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Файл конфігурації не знайдено: {path}\n"
            "Переконайтесь, що файл config/config.yaml існує."
        )

    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.debug(f"[Config] Завантажено з {path} (PyYAML)")
        return config or {}

    except ImportError:

        logger.warning(
            "[Config] PyYAML не встановлено. "
            "Використовується спрощений парсер. "
            "Встановіть: pip install pyyaml"
        )
        return _simple_yaml_parse(path)

def _simple_yaml_parse(path: str) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    current_section = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:

            line = line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            if line.startswith("  ") and current_section:
                stripped = line.strip()
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    v = v.strip().split("#")[0].strip()
                    if v and v != "null":
                        try:
                            v = int(v)
                        except ValueError:
                            pass
                    else:
                        v = None
                    config[current_section][k.strip()] = v
            else:

                stripped = line.strip()
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    v = v.strip().split("#")[0].strip()
                    if v:
                        config[k.strip()] = v
                    else:
                        current_section = k.strip()
                        config[current_section] = {}

    return config
