import requests
from zhixuewang.exceptions import LoginError, UserOrPassError, UserNotFoundError
from zhixuewang.models import Account
from zhixuewang.session import get_basic_session, check_is_student
from loguru import logger
import json
import base64

from zhixuewang.student import StudentAccount
from zhixuewang.teacher import TeacherAccount
from zhixuewang.urls import Url

from models import LoginCaptchaError
from msg import send_private_message

MAX_RETRIES = 5

def gen_encrypted_password(password):
    if len(password) != 32:
        password = (
            pow(
                int.from_bytes(password.encode()[::-1], "big"),
                65537,
                186198350384465244738867467156319743461,
            )
            .to_bytes(16, "big")
            .hex()
        )  # by immoses648
    return password

def get_session_by_captcha(username: str, password: str) -> requests.Session:
    """通过用户名和密码获取 session，使用验证码

    Args:
        username (str): 用户名
        password (str): 密码

    Raises:
        UserOrPassError: 用户名或密码错误
        UserNotFoundError: 未找到用户
        LoginError: 登录错误

    Returns:
        requests.session:
    """
    password=gen_encrypted_password(password)
    session = get_basic_session()

    # 获取验证码
    logger.info("Getting captcha")
    for attempt in range(MAX_RETRIES):
        try:
            captcha_data = session.get("http://54.169.202.224:8080/get_geetest", timeout=5).json()["data"]
            break
        except requests.exceptions.RequestException:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Failed to get captcha after {MAX_RETRIES} attempts")
                send_private_message(337249336, "验证码获取失败。")
                raise LoginCaptchaError(f"Failed to get captcha after {MAX_RETRIES} attempts")
    if captcha_data["result"] != "success":
        logger.error("Failed to get captcha")
        raise LoginError("Failed to get captcha")
    login_url = "https://pass.changyan.com/login/checkLogin"
    # Zhixue URL: https://www.zhixue.com/edition/login?from=web_login
    data = {
        "i": username,
        "p": password,
        "f": "1",
        "c": "",
        "a": "0",
        "m": "",
        "dm": "web",
        "co": captcha_data["seccode"]["captcha_output"],
        "gt": captcha_data["seccode"]["gen_time"],
        "ln": captcha_data["seccode"]["lot_number"],
        "pt": captcha_data["seccode"]["pass_token"],
        "ct": "web",
        "cat": "third"
    }
    captcha_result = session.post(login_url, data=data).json()
    # if captcha_result["result"] != "success":
    if captcha_result["Msg"] != "获取用户信息成功":
        logger.error(f"Failed to login: {captcha_result['message']}")
        raise LoginError(f"Failed to login: {captcha_result['message']}")
    # captcha_id = captcha_result["data"]["captcha_id"]
    captcha_id = json.loads(captcha_result["Data"])["captchaResult"]
    # 原登录逻辑
    r = session.get(Url.SSO_URL)
    json_obj = json.loads(r.text.strip().replace("\\", "").replace("'", "")[1:-1])
    if json_obj["code"] != 1000:
        raise LoginError(json_obj["data"])
    lt = json_obj["data"]["lt"]
    execution = json_obj["data"]["execution"]
    r = session.get(
        Url.SSO_URL,
        params={
            "captchaId": captcha_id,
            "captchaType": "third",
            "thirdCaptchaParam": captcha_data["seccode"],
            "encode": "true",
            "sourceappname": "tkyh,tkyh",
            "_eventId": "submit",
            "appid": "zx-container-client",
            "client": "web",
            "type": "loginByNormal",
            "key": "auto",
            "lt": lt,
            "execution": execution,
            "customLogoutUrl": "https://www.zhixue.com/login.html",
            "username": username,
            "password": password,
        },
    )
    json_obj = json.loads(r.text.strip().replace("\\", "").replace("'", "")[1:-1])
    if json_obj["code"] != 1001:
        if json_obj["code"] == 1002:
            raise UserOrPassError()
        if json_obj["code"] == 2009:
            raise UserNotFoundError()
        raise LoginError(json_obj["data"])
    ticket = json_obj["data"]["st"]
    session.post(
        Url.SERVICE_URL,
        data={
            "action": "login",
            "ticket": ticket,
        },
    )
    session.cookies.set("uname", base64.b64encode(username.encode()).decode())
    session.cookies.set("pwd", base64.b64encode(password.encode()).decode())
    return session

def login_by_captcha(username: str, password: str) -> Account:
    """通过用户名和密码登录，使用验证码

    Args:
        username (str): 用户名
        password (str): 密码

    Raises:
        UserOrPassError: 用户名或密码错误
        UserNotFoundError: 未找到用户
        LoginError: 登录错误

    Returns:
        Person
    """
    session = get_session_by_captcha(username, password)
    if check_is_student(session):
        return StudentAccount(session).set_base_info()
    return TeacherAccount(session).set_base_info().set_advanced_info()

def update_login_status_self(account: Account):
        """更新登录状态. 如果 session 过期自动重新获取"""
        r = account._session.get(Url.GET_LOGIN_STATE)
        data = r.json()
        if data["result"] == "success":
            return account
        # session过期
        password = base64.b64decode(account._session.cookies["pwd"].encode()).decode()
        account._session = get_session_by_captcha(account.username, password)
        return account