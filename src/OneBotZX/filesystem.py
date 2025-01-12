import os
import pickle

from loguru import logger

if not os.path.exists("./.zx/data"):
    os.makedirs("./.zx/data")
if not os.path.exists("./.zx/config"):
    os.makedirs("./.zx/config")
if not os.path.exists("./.zx/cache"):
    os.makedirs("./.zx/cache")


def save_cache(file: str, data):
    with open(f"./.zx/data/{file}.pkl", "wb") as f:
        pickle.dump(data, f)
        logger.success(f"Successfully saved cache: {file}")


def load_cache(file: str, typ="dict"):
    try:
        with open(f"./.zx/data/{file}.pkl", "rb") as f:
            logger.success(f"Successfully loaded cache: {file}")
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        if typ == "dict":
            return {}
        return []


def save_ban_list(ban_list):
    with open("./.zx/config/ban_list.pkl", "wb") as f:
        pickle.dump(ban_list, f)
        logger.success("Successfully saved ban_list")


def load_ban_list():
    try:
        with open("./.zx/config/ban_list.pkl", "rb") as f:
            logger.success("Successfully loaded ban_list")
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load ban_list: {e}")
        return []


def clean_cache_data(file: str):
    if file == "all":
        try:
            for file in os.listdir("./.zx/data"):
                os.remove(f"./.zx/data/{file}")
            logger.success("Successfully cleaned all cache data")
            return True
        except Exception as e:
            logger.error(f"Failed to clean cache data: {e}")
            return False
    try:
        os.remove(f"./.zx/data/{file}.pkl")
        logger.success(f"Successfully cleaned cache data: {file}")
        return True
    except Exception as e:
        logger.error(f"Failed to clean cache data: {e}")
        return False


def clean_cache_file():
    try:
        for file in os.listdir("./.zx/cache"):
            os.remove(f"./.zx/cache/{file}")
        logger.success("Successfully cleaned all cache file")
        return True
    except Exception as e:
        logger.error(f"Failed to clean cache: {e}")
        return False
