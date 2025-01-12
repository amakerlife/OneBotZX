import os
import time
from functools import wraps
from queue import Queue

from flask import Flask, request
from flask_limiter import Limiter
from loguru import logger

import zhixue
from config_loader import message_config
from filesystem import load_ban_list, save_ban_list, clean_cache_data, clean_cache_file
from msg import send_private_message, send_private_file, send_private_img, approve_friend_request
from models import CommandError

# Config Start
chat_prefix = message_config.chat_prefix
admins = message_config.admins
super_users = message_config.super_users
reply_limit = message_config.reply_limit
max_reply = message_config.max_reply

wait_for_login = {}
ban_list = []

logger.add(f"./.zx/log/zxbot.log", encoding="utf-8", rotation="00:00", enqueue=True)
# Config End


# Flask Config Start
rate_limit_status = {}
app = Flask(__name__)


def get_sender_id():
    request_data = request.get_json()
    return str(request_data.get("sender", {}).get("user_id", ""))


limiter = Limiter(app=app, key_func=get_sender_id, default_limits=[])
queue = Queue()


@app.before_request
def queue_requests():
    queue.put(time.time())


@app.after_request
def process_queue(response):
    current_time = time.time()
    request_time = queue.get()

    wait_time = reply_limit - (current_time - request_time)
    if wait_time > 0:
        time.sleep(wait_time)

    return response


def should_limit():
    try:
        message = request.get_json().get("message", [])[0].get("data", {}).get("text", "")
    except Exception:
        return False
    return not message.startswith(chat_prefix)


@app.route("/", methods=["POST"])
@limiter.limit("20 per 5 minutes", exempt_when=should_limit)
@limiter.limit("50 per hour", exempt_when=should_limit)
def handle_request():
    request_data = request.get_json()
    if str(request_data.get("sender", {}).get("user_id", "")) in rate_limit_status:
        del rate_limit_status[str(request_data.get("sender", {}).get("user_id", ""))]

    if request_data.get("post_type") == "request" and request_data.get("request_type") == "friend":
        handle_friend_request(request_data)

    if request_data.get("post_type") == "message" or request_data.get("post_type") == "message_sent":
        handle_message(request_data)

    return '', 204


@app.errorhandler(429)
def ratelimit_handler(e):
    sender_id = str(request.get_json().get("sender", {}).get("user_id", ""))
    if sender_id in ban_list:
        return '', 403
    if sender_id not in rate_limit_status:
        rate_limit_status[sender_id] = 0
        send_private_message(sender_id, "已触发请求数量限制，请 10 分钟后再试。多次触发将导致封禁。")
    logger.debug(f"Rate limit exceeded: {sender_id}")
    rate_limit_status[sender_id] += 1
    if rate_limit_status[sender_id] >= max_reply:
        ban_list.append(int(sender_id))
        save_ban_list(ban_list)
        send_private_message(sender_id, "因多次触发请求频率限制，已被封禁。请联系管理员。")
        logger.warning(f"{sender_id} has been banned due to frequent requests.")
    return '', 429

# Flask Config End


def require_login(f: callable):
    @wraps(f)
    def wrapper(sender_id, message, *args, **kwargs):
        if not zhixue.stu_list.get(sender_id):
            raise CommandError("未登录智学网账号。")
        return f(sender_id, message, *args, **kwargs)
    return wrapper


def handle_help_request(sender_id, message):
    send_private_message(sender_id, f"帮助信息：\n"
                                    f"{chat_prefix} login <学生账号> <密码> - 登录学生账号\n"
                                    f"{chat_prefix} logout - 登出学生账号\n"
                                    f"{chat_prefix} info - 获取用户信息\n"
                                    f"{chat_prefix} exam list - 获取考试列表\n"
                                    f"{chat_prefix} exam score <考试ID> - 获取考试成绩（初次使用可能较慢）\n"
                                    f"{chat_prefix} exam answersheet <考试ID> - 获取考试答题卡\n"
                                    f"{chat_prefix} help - 获取帮助信息\n"
                                    f"\n提醒：提供的密码仅用于验证身份及获取数据。登录完成后您可以立即撤回密码。\n"
                                    f"例如，使用 /zx login abcd 1234 来登录。\n"
                                    f"若在日后使用时发现机器人状态为离线，请联系管理员 {admins[0]} 解决。\n"
                                    f"由于风控和请求数量限制，机器人可能需要至多 2 分钟来响应您的请求。\n"
                                    f"使用本机器人即表示您同意遵守相关规定，并为使用本机器人的所有行为负责。")
    if int(sender_id) in admins:
        send_private_message(sender_id, f"欢迎您，管理员 {sender_id}：\n"
                                        f"{chat_prefix} admin rm data <stu_list|tch_list|exam_scores|all> - 清除缓存数据\n"
                                        f"{chat_prefix} admin rm cache - 清除缓存\n"
                                        f"{chat_prefix} admin ban <add|rm> <QQ 号> - 禁用或解禁用户\n"
                                        f"{chat_prefix} admin forcelogout <QQ 号> - 强制登出 QQ 对应的学生账号\n"
                                        f"{chat_prefix} admin examxlsx <考试ID> - 获取考试成绩单\n"
                                        f"{chat_prefix} admin examanswersheet <id|name> <学生ID> <考试ID> - 获取考试答题卡\n")
    if int(sender_id) in super_users:
        send_private_message(sender_id, f"欢迎您，高级用户 {sender_id}：\n"
                                        f"{chat_prefix} sudo examxlsx <考试ID> - 获取考试成绩单\n")


def handle_login_request(sender_id, message):
    username, password = message.split(" ", 2)
    logger.info(f"Try to login: {username}")
    status, info = zhixue.login_stu(sender_id, username, password)
    if status == 0:
        logger.info(f"{sender_id} successfully logged in: {username}")
        send_private_message(sender_id, "登录成功。")
    else:
        logger.info(f"{sender_id} failed login in: {username}")
        if status == 1:
            del wait_for_login[sender_id]
            raise CommandError("登录失败。")
        elif status == 2:
            raise CommandError(f"已登录智学网账号 {info}。如需登录新账号，请先发送 /zx logout。")
        elif status == 3:
            if sender_id in wait_for_login:
                status, info = zhixue.login_stu(sender_id, username, password)
                if status == 0:
                    logger.info(f"{sender_id} successfully logged in: {username}")
                    original_qqid = wait_for_login[sender_id]
                    zhixue.logout_stu(original_qqid)
                    send_private_message(sender_id, f"登录成功，已下线 {wait_for_login.get(sender_id)} 的登录状态。")
                    send_private_message(original_qqid, f"您的智学网账号 {username} 已被 {sender_id} 使用。"
                                                        f"如果非本人操作，请及时修改密码。")
                else:
                    raise CommandError("登录失败。")
                del wait_for_login[sender_id]
                return
            send_private_message(sender_id, f"该智学网账号已被 QQ 号 {info} 占用，请再次登录以下线 {info}。")
            wait_for_login[sender_id] = info
        elif status == 4:
            raise CommandError("网络异常，请联系管理员。")


@require_login
def handle_logout_request(sender_id, message):
    username, status = zhixue.logout_stu(sender_id)
    if status:
        logger.info(f"{sender_id} successfully logged out: {username}")
        send_private_message(sender_id, f"成功登出: {username}。")
    else:
        logger.warning(f"{sender_id} failed login out: {username}")
        raise CommandError("登出失败，出现未知错误。")


@require_login
def handle_info_request(sender_id, message):
    details = zhixue.get_user_info(sender_id)
    if details:
        send_private_message(sender_id, details)
    else:
        raise CommandError("获取用户信息失败。")


@require_login
def handle_exam_request(sender_id, message):
    # if not zhixue.stu_list.get(sender_id):
    #     send_private_message(sender_id, "未登录智学网账号。")
    #     return
    if message.startswith("list"):
        exams = zhixue.get_exams(sender_id)
        if exams:
            send_private_message(sender_id, exams)
        else:
            raise CommandError("获取考试列表失败。")
    elif message.startswith("score"):
        examid = message.split(" ", 2)[1]
        details = zhixue.get_rank_by_stu_code(sender_id, examid)
        if details:
            send_private_message(sender_id, details)
        else:
            raise CommandError("获取考试成绩失败。")
    elif message.startswith("answersheet"):
        examid = message.split(" ", 2)[1]
        file_paths = zhixue.get_answersheet_by_qqid(sender_id, examid)
        for file_path in file_paths:
            send_private_img(sender_id, f"file://{os.path.abspath(file_path)}")
    else:
        raise CommandError("未知指令，请使用 /zx help 查看帮助。")


def handle_admin_request(sender_id, message):
    if int(sender_id) not in admins:
        logger.info(f"{sender_id} tried to use admin command: {message}")
        raise CommandError("您无权使用该指令。")
    if message.startswith("rm"):
        message = message[len("rm") + 1:].strip()
        if message.startswith("data"):
            message = message[len("data") + 1:].strip()
            if clean_cache_data(message):
                send_private_message(sender_id, f"已清除缓存数据：{message}")
            else:
                raise CommandError(f"清除缓存数据失败：{message}，请查看日志。")
        elif message.startswith("cache"):
            if clean_cache_file():
                send_private_message(sender_id, "已清除缓存。")
            else:
                raise CommandError("清除缓存失败，请查看日志。")
    elif message.startswith("ban"):
        message = message[len("ban") + 1:].strip()
        action, qqid = message.split(" ", 2)
        if action == "add":
            ban_list.append(int(qqid))
            save_ban_list(ban_list)
            send_private_message(sender_id, f"已禁用用户：{qqid}")
        elif action == "rm":
            ban_list.remove(int(qqid))
            save_ban_list(ban_list)
            send_private_message(sender_id, f"已解禁用户：{qqid}")
    elif message.startswith("forcelogout"):
        qqid = message.split(" ", 2)[1]
        username, status = zhixue.logout_stu(qqid)
        if status:
            send_private_message(sender_id, f"成功登出: {username}。")
        else:
            raise CommandError("登出失败，疑似未登录智学网账号。")
    elif message.startswith("examxlsx"):
        examid = message.split(" ", 2)[1]
        file_path = zhixue.get_exam_rank(sender_id, examid)
        if file_path:
            send_private_file(sender_id, f"file://{os.path.abspath(file_path)}")
        else:
            raise CommandError("获取考试排名失败。")
    elif message.startswith("examanswersheet"):
        message = message[len("examanswersheet") + 1:].strip()
        method, stuid, examid = message.split(" ", 3)
        if method == "id":
            file_paths = zhixue.get_answersheet_by_stuid(sender_id, stuid, examid)
            for file_path in file_paths:
                send_private_img(sender_id, f"file://{os.path.abspath(file_path)}")
        elif method == "name":
            file_paths = zhixue.get_answersheet_by_stuname(stuid, sender_id, examid)
            for file_path in file_paths:
                send_private_img(sender_id, f"file://{os.path.abspath(file_path)}")


def handle_sudo_request(sender_id, message):
    if int(sender_id) not in super_users:
        raise CommandError("您无权使用该指令。")
    if message.startswith("examxlsx"):
        examid = message.split(" ", 2)[1]
        file_path = zhixue.get_exam_rank(sender_id, examid)
        if file_path:
            send_private_file(sender_id, f"file://{os.path.abspath(file_path)}")
        else:
            raise CommandError("获取考试排名失败。")


def handle_friend_request(request_data):
    flag = request_data.get("flag", "")
    if approve_friend_request(flag):
        logger.info(f"Approved friend request: {flag}")
    else:
        logger.error(f"Failed to approve friend request: {flag}")


def handle_message(request_data):
    self_id = str(request_data.get("self_id", ""))
    sender_id = str(request_data.get("sender", {}).get("user_id", ""))
    sender_nickname = str(request_data.get("sender", {}).get("nickname", ""))
    message_type = request_data.get("message_type", "")
    message = request_data.get("message", [])[0].get("data", {}).get("text", "")

    # TODO: 教师账户不可用提示。

    if message_type == "private":  # 私聊消息
        if int(sender_id) in ban_list:
            logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message} (BANNED)")
            return
        if message.startswith(chat_prefix):
            logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message}")
            message = message[len(chat_prefix) + 1:].strip()
            command = message.split(" ", 1)[0]
            message = message[len(command) + 1:].strip()
            command_handlers = {
                "help": handle_help_request,
                "login": handle_login_request,
                "logout": handle_logout_request,
                "info": handle_info_request,
                "exam": handle_exam_request,
                "admin": handle_admin_request,
                "sudo": handle_sudo_request,
            }
            handler = command_handlers.get(command)
            if handler:
                try:
                    handler(sender_id, message)
                except CommandError as e:
                    send_private_message(sender_id, str(e))
                except Exception as e:
                    if int(sender_id) in admins:
                        send_private_message(sender_id, f"发生错误: {str(e)[:100]}")
                    else:
                        send_private_message(sender_id, "发生未知错误，请联系管理员。")
                    logger.exception(f"An error occurred when handling {message}")
            else:
                send_private_message(sender_id, f"未知指令，请使用 {chat_prefix} help 查看帮助。")
        # else:
        #     logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message} (IGNORED)")


if __name__ == "__main__":
    zhixue.load_all_stu_list()
    ban_list = load_ban_list()
    app.run(host="127.0.0.1", port=5010, threaded=False)
