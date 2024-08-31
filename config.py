import yaml
from loguru import logger

config_path = "config.yml"


class ConfigError(Exception):
    pass


class OnebotConfig:
    def __init__(self, http_url: str, access_token: str):
        self.http_url = http_url
        self.access_token = access_token


class MessageConfig:
    def __init__(self, chat_prefix: str, admins: list[int]):
        self.chat_prefix = chat_prefix
        self.admins = admins


class ZhixueConfig:
    def __init__(self, teacher_account: str, teacher_password: str):
        self.teacher_account = teacher_account
        self.teacher_password = teacher_password


with open(config_path, "r", encoding="utf-8") as file:
    config_data = yaml.safe_load(file)

try:
    onebot_config = OnebotConfig(**config_data.get("onebot", {}))
    message_config = MessageConfig(**config_data.get("message", {}))
    zhixue_config = ZhixueConfig(**config_data.get("zhixue", {}))
    logger.success("Config loaded successfully")
except Exception as e:
    logger.error(f"FATAL ERROR: Failed to load config: {e}")
    raise ConfigError(f"Failed to load config: {e}")
