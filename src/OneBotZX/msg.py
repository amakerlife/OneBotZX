import json

import requests
from loguru import logger

from config_loader import onebot_config

http_url = onebot_config.http_url
access_token = onebot_config.access_token


def truncate_string(s, length=30):
    if len(s) > length:
        return s[:length] + "..."
    else:
        return s


def send_request(url, headers, data, content, msg_type = "message"):
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        result = response.json()
        if result["status"] == "ok":
            if msg_type == "message":
                logger.success(f"Successfully sent message: {truncate_string(content)}")
            elif msg_type == "image":
                logger.success(f"Successfully sent image: {content}")
            elif msg_type == "file":
                logger.success(f"Successfully sent file: {content}")
            elif msg_type == "friend_request":
                logger.success(f"Successfully approved friend request: {content}")
            return True
        else:
            if msg_type == "message":
                logger.error(f"Failed to send message, response: {str(result)}")
            elif msg_type == "image":
                logger.error(f"Failed to send image, response: {str(result)}")
            elif msg_type == "file":
                logger.error(f"Failed to send file, response: {str(result)}")
            elif msg_type == "friend_request":
                logger.error(f"Failed to approve friend request, response: {str(result)}")
            return False
    else:
        if msg_type == "message":
            logger.error(f"Failed to send message, status code: {str(response.status_code)}")
        elif msg_type == "image":
            logger.error(f"Failed to send image, status code: {str(response.status_code)}")
        elif msg_type == "file":
            logger.error(f"Failed to send file, status code: {str(response.status_code)}")
        elif msg_type == "friend_request":
            logger.error(f"Failed to approve friend request, status code: {str(response.status_code)}")
        return False


def approve_friend_request(flag, approve=True):
    url = f"{http_url}/set_friend_add_request"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "flag": flag,
        "approve": approve
    }
    return send_request(url, headers, data, flag, "friend_request")


def send_private_message(user_id, content):
    url = f"{http_url}/send_private_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "user_id": user_id,
        "message": [
            {
                "type": "text",
                "data": {"text": content}
            }
        ]
    }
    return send_request(url, headers, data, content)


def send_group_message(group_id, sender_id, content):
    url = f"{http_url}/send_group_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "group_id": group_id,
        "message": [
            {
                "type": "at",
                "data": {"qq": sender_id}
            },
            {
                "type": "text",
                "data": {"text": " " + content}
            }
        ]
    }
    return send_request(url, headers, data, content)


def send_private_img(user_id, content):
    url = f"{http_url}/send_private_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "user_id": user_id,
        "message": [
            {
                "type": "image",
                "data": {"file": content}
            }
        ]
    }
    return send_request(url, headers, data, content, "image")


def send_group_img(group_id, sender_id, content):
    url = f"{http_url}/send_group_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "group_id": group_id,
        "message": [
            {
                "type": "at",
                "data": {"qq": sender_id}
            },
            {
                "type": "image",
                "data": {"file": content}
            }
        ]
    }
    return send_request(url, headers, data, content, "image")


def send_private_file(user_id, file_path):
    url = f"{http_url}/send_private_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "user_id": user_id,
        "message": [
            {
                "type": "file",
                "data": {
                    "file": file_path,
                    # "name": file_name
                }
            }
        ]
    }
    return send_request(url, headers, data, file_path, "file")
