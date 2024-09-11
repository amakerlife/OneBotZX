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
    def __init__(self, teacher_accounts: list[str], teacher_passwords: list[str], teacher_login_method: list[str]):
        self.teacher_accounts = teacher_accounts
        self.teacher_passwords = teacher_passwords
        self.teacher_login_method = teacher_login_method


with open(config_path, "r", encoding="utf-8") as file:
    config_data = yaml.safe_load(file)

try:
    onebot_config = OnebotConfig(**config_data.get("onebot", {}))
    message_config = MessageConfig(**config_data.get("message", {}))
    zhixue_config = ZhixueConfig(**config_data.get("zhixue", {}))
    logger.success("Config loaded successfully")
except Exception as e:
    logger.critical(f"FATAL ERROR: Failed to load config: {e}")
    raise ConfigError(f"Failed to load config: {e}")
