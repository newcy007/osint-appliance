import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def load_global_config():
    load_dotenv(ROOT / ".env")

    cfg_path = ROOT / "config" / "config.yml"
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    # Resolve environment variables
    for api_name, api_cfg in cfg.get("apis", {}).items():
        env_var = api_cfg.get("key_env")
        if env_var:
            api_cfg["key"] = os.getenv(env_var)

    return cfg
