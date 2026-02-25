import os
from dotenv import load_dotenv
from pathlib import Path

# check for explicit environment variable
env_path = os.getenv("BACLINK_ENV_PATH") 

#
if not env_path and Path("/opt/baclink.config/.env").exists():
    env_path = "/opt/baclink/config/.env"

env_file = Path(env_path)

#still no .env path...
if not env_file.exists():
    raise FileNotFoundError(f"Required .env file not found at {env_file}")

try:
    load_dotenv(env_file)
except Exception as e:
    print(f"config.py: Error loading .env file {e}")

OPCUA_SERVER_URL = os.getenv("OPCUA_SERVER_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_PATH = os.getenv("LOG_PATH")
PLC_TREE_HEAD = os.getenv("PLC_TREE_HEAD")


UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS"))
MAX_UPDATE_INTERVAL_MINUTES = int(os.getenv("MAX_UPDATE_INTERVAL_MINUTES"))
SUBSCRIBE_DATA_TYPES = [item.lower() for item in os.getenv("SUBSCRIBE_DATA_TYPES").split(",")]