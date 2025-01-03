import os

import yaml
from loguru import logger

config_path = "config/config.yml"


class ConfigError(Exception):
    pass


class OnebotConfig:
    def __init__(self, http_url: str, access_token: str):
        self.http_url = http_url
        self.access_token = access_token


class MessageConfig:
    def __init__(self, chat_prefix: str, admins: list[int], super_users: list[int], reply_limit=1, max_reply=0):
        self.chat_prefix = chat_prefix
        self.admins = admins
        self.super_users = super_users
        self.reply_limit = reply_limit
        self.max_reply = max_reply


class ZhixueConfig:
    def __init__(self, teacher_accounts: list[str], teacher_passwords: list[str], teacher_login_method: list[str],
                 captcha_api: str):
        self.teacher_accounts = teacher_accounts
        self.teacher_passwords = teacher_passwords
        self.teacher_login_method = teacher_login_method
        self.captcha_api = captcha_api

class AssetsConfig:
    def __init__(self, font_path: str):
        self.font_path = font_path
        if not os.path.exists(font_path) or not os.path.isfile(font_path):
            raise ConfigError(f"No such file: {font_path}")


with open(config_path, "r", encoding="utf-8") as file:
    config_data = yaml.safe_load(file)

try:
    onebot_config = OnebotConfig(**config_data.get("onebot", {}))
    message_config = MessageConfig(**config_data.get("message", {}))
    zhixue_config = ZhixueConfig(**config_data.get("zhixue", {}))
    assets_config = AssetsConfig(**config_data.get("assets", {}))
    logger.success("Successfully loaded config")
except Exception as e:
    logger.critical(f"FATAL ERROR: Failed to load config: {e}")
    raise ConfigError(f"Failed to load config: {e}")
