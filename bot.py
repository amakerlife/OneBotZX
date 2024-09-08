import os

from flask import Flask, request
from loguru import logger

import zhixue
from config import message_config
from filesystem import load_ban_list, save_ban_list, clean_cache_data, clean_cache_file
from msg import send_private_message, send_private_file, send_private_img, approve_friend_request

app = Flask(__name__)

chat_prefix = message_config.chat_prefix
admins = message_config.admins

wait_for_login = {}
ban_list = []


@app.route("/", methods=["POST"])
def handle_request():
    request_data = request.get_json()

    if request_data.get("post_type") == "request" and request_data.get("request_type") == "friend":
        process_friend_request(request_data)

    if request_data.get("post_type") == "message" or request_data.get("post_type") == "message_sent":
        process_message(request_data)

    return '', 204


def process_friend_request(request_data):
    flag = request_data.get("flag", "")
    if approve_friend_request(flag):
        logger.info(f"Approved friend request: {flag}")
    else:
        logger.warning(f"Failed to approve friend request: {flag}")


def process_message(request_data):
    self_id = str(request_data.get("self_id", ""))
    sender_id = str(request_data.get("sender", {}).get("user_id", ""))
    sender_nickname = str(request_data.get("sender", {}).get("nickname", ""))
    message_type = request_data.get("message_type", "")
    message = request_data.get("message", [])[0].get("data", {}).get("text", "")

    if message_type == "private":  # 私聊消息
        if int(sender_id) in ban_list:
            logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message} (BANNED)")
            return
        if message.startswith(chat_prefix):
            logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message}")
            message = message[len(chat_prefix) + 1:].strip()
            if message.startswith("help"):
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
                                                f"若在自后使用时发现机器人状态为离线，请联系管理员 3372493336 解决。\n"
                                                f"使用本机器人即表示您同意遵守相关规定，并为使用本机器人的所有行为负责。")
                if int(sender_id) in admins:
                    send_private_message(sender_id, f"欢迎您，管理员 {sender_id}：\n"
                                                    f"{chat_prefix} admin rm data <stu_list|tch_list|exam_scores|all> - 清除缓存数据\n"
                                                    f"{chat_prefix} admin rm cache - 清除缓存\n"
                                                    f"{chat_prefix} admin ban <add|rm> <QQ 号> - 禁用或解禁用户\n"
                                                    f"{chat_prefix} admin forcelogout <QQ 号> - 强制登出 QQ 对应的学生账号\n"
                                                    f"{chat_prefix} admin examxlsx <考试ID> - 获取考试成绩单\n"
                                                    f"{chat_prefix} admin examanswersheet <id|name> <学生ID> <考试ID> - 获取考试答题卡\n")
                return

            elif message.startswith("login"):
                message = message[len("login") + 1:].strip()
                username, password = message.split(" ", 2)
                logger.info(f"Try to login: {username}")
                status, info = zhixue.login_stu(sender_id, username, password)
                if status == 0:
                    logger.info(f"{sender_id} Successfully logged in: {username}")
                    send_private_message(sender_id, "登录成功。")
                else:
                    if status == 1:
                        logger.warning(f"{sender_id} failed login in: {username}")
                        send_private_message(sender_id, "登录失败。")
                        del wait_for_login[sender_id]
                    elif status == 2:
                        logger.warning(f"{sender_id} repeat login in: {info}")
                        send_private_message(sender_id, f"已登录智学网账号 {info}。")
                    elif status == 3:
                        if sender_id in wait_for_login:
                            zhixue.logout_stu(wait_for_login[sender_id])
                            status = zhixue.login_stu(sender_id, username, password)
                            if status == 0:
                                send_private_message(sender_id,
                                                 f"登录成功，已下线 {wait_for_login.get(sender_id)} 的登录状态。")
                            else:
                                send_private_message(sender_id, "登录失败。")
                            send_private_message(wait_for_login[sender_id], f"您的智学网账号已被 {sender_id} 使用。"
                                                                            f"如果非本人操作，请及时修改密码。")
                            del wait_for_login[sender_id]
                            return
                        logger.warning(f"{sender_id} failed login in: {username}({info})")
                        send_private_message(sender_id, f"该智学网账号已被 QQ 号 {info} 占用，请再次登录以下线 {info}。")
                        wait_for_login[sender_id] = info
                    elif status == 4:
                        send_private_message(sender_id, "网络异常，请联系管理员。")
                return

            elif message.startswith("logout"):
                username, status = zhixue.logout_stu(sender_id)
                if status:
                    logger.info(f"{sender_id} Successfully logged out: {username}")
                    send_private_message(sender_id, f"成功登出: {username}。")
                else:
                    logger.warning(f"{sender_id} failed login out: {username}")
                    send_private_message(sender_id, "登出失败，疑似未登录智学网账号。")
                return

            elif message.startswith("info"):
                if not zhixue.stu_list.get(sender_id):
                    send_private_message(sender_id, "未登录智学网账号。")
                    return
                details = zhixue.get_user_info(sender_id)
                if details:
                    send_private_message(sender_id, details)
                else:
                    send_private_message(sender_id, "获取用户信息失败！")
                return

            elif message.startswith("exam"):
                if not zhixue.stu_list.get(sender_id):
                    send_private_message(sender_id, "未登录智学网账号。")
                    return
                message = message[len("exam") + 1:].strip()
                if message.startswith("list"):
                    exams = zhixue.get_exams(sender_id)
                    if exams:
                        send_private_message(sender_id, exams)
                    else:
                        send_private_message(sender_id, "获取考试列表失败！")
                elif message.startswith("score"):
                    examid = message.split(" ", 2)[1]
                    details = zhixue.get_rank_by_stu_code(sender_id, examid)
                    if details:
                        send_private_message(sender_id, details)
                    else:
                        send_private_message(sender_id, "获取考试排名失败！")
                elif message.startswith("answersheet"):
                    examid = message.split(" ", 2)[1]
                    file_paths = zhixue.get_answersheet_by_qqid(sender_id, examid)
                    for file_path in file_paths:
                        send_private_img(sender_id, f"file://{os.path.abspath(file_path)}")
                else:
                    send_private_message(sender_id, f"未知指令，请使用 {chat_prefix} help 查看帮助。")
                return

            elif message.startswith("admin"):
                if int(sender_id) not in admins:
                    send_private_message(sender_id, "您无权使用该指令。")
                    logger.warning(f"{sender_id} tried to use admin command: {message}")
                    return
                logger.warning(f"Admin {sender_id} used admin command: {message}")
                message = message[len("admin") + 1:].strip()
                if message.startswith("rm"):
                    message = message[len("rm") + 1:].strip()
                    if message.startswith("data"):
                        message = message[len("data") + 1:].strip()
                        if clean_cache_data(message):
                            send_private_message(sender_id, f"已清除缓存数据：{message}")
                        else:
                            send_private_message(sender_id, f"清除缓存数据失败：{message}，请查看日志。")
                    elif message.startswith("cache"):
                        if clean_cache_file():
                            send_private_message(sender_id, "已清除缓存。")
                        else:
                            send_private_message(sender_id, "清除缓存失败，请查看日志。")
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
                        send_private_message(sender_id, "登出失败，疑似未登录智学网账号。")
                elif message.startswith("examxlsx"):
                    examid = message.split(" ", 2)[1]
                    file_path = zhixue.get_exam_rank(sender_id, examid)
                    if file_path:
                        send_private_file(sender_id, f"file://{os.path.abspath(file_path)}")
                    else:
                        send_private_message(sender_id, "获取考试排名失败！")
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

                return

            else:
                send_private_message(sender_id, f"未知指令，请使用 {chat_prefix} help 查看帮助。")
        else:
            logger.info(f"Private: {sender_id}({sender_nickname}) -> {self_id}: {message} (IGNORED)")


if __name__ == "__main__":
    zhixue.load_all_stu_list()
    ban_list = load_ban_list()
    # 启动 Flask 应用程序
    app.run(host="127.0.0.1", port=5010)
