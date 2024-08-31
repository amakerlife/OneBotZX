from msg import send_private_message

class ZhixueError(Exception):
    pass

class LoginCaptchaError(Exception):
    pass

class FailedGetTeacherAccountError(Exception):
    send_private_message(Exception, "无法获取所在学校的信息，请联系管理员。")