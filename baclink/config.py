import os
from dotenv import load_dotenv, find_dotenv
import logging

logger = logging.getLogger(__name__)

try:
    load_dotenv(find_dotenv())
except Exception as e:
    logger.exception(f"Error loading .env file {e}")

OPCUA_SERVER_URL = os.getenv("OPCUA_SERVER_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_PATH = os.getenv("LOG_PATH")
PLC_TREE_HEAD = os.getenv("PLC_TREE_HEAD")


UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS"))
MAX_UPDATE_INTERVAL_MINUTES = int(os.getenv("MAX_UPDATE_INTERVAL_MINUTES"))
SUBSCRIBE_DATA_TYPES = [item.lower() for item in os.getenv("SUBSCRIBE_DATA_TYPES").split(",")]