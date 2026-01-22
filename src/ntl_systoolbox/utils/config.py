import yaml
import os

def load_config(path="config/config.yml"):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {}
