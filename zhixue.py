import json
import os
import time

from loguru import logger
from openpyxl import Workbook
from zhixuewang.models import StuPerson

from login import update_login_status_self, login_by_captcha
from models import ZhixueError, LoginCaptchaError, FailedGetTeacherAccountError

from filesystem import save_cache, load_cache
from teacher import get_school_rank_by_stu_code, get_exam_all_rank, get_exam_subjects, process_answersheet, \
    get_stuid_by_stuname
from config import zhixue_config

teacher_usernames = zhixue_config.teacher_accounts
teacher_passwords = zhixue_config.teacher_passwords

stu_list = {}
tch_list = load_cache("tch_list")
exam_scores_by_stu = {}
exam_scores = {}

# tch = login_by_captcha(USERNAME_TEACHER, PASSWORD_TEACHER)

for teacher_account in teacher_usernames:
    for tch_school in tch_list:
        if tch_list[tch_school].username == teacher_account:
            break
    else:
        tch_account = login_by_captcha(teacher_account, teacher_passwords[teacher_usernames.index(teacher_account)])
        tch_school = tch_account.school.id
        tch_list[tch_school] = tch_account
    # if teacher_account not in tch_list:
    #     tch_account = login_by_captcha(teacher_account, teacher_passwords[teacher_usernames.index(teacher_account)])
    #     tch_school = tch_account.school.id
    #     tch_list[tch_school] = tch_account
save_cache("tch_list", tch_list)

def load_all_stu_list():
    global stu_list
    stu_list = load_cache("stu_list")


def get_user(qqid):
    """
    获得 QQ 号对应的学生账号
    Args:
        qqid: QQ 号
    Return:
        StudentAccount: 学生账号
        bool: 是否存在
    """
    global stu_list
    if qqid in stu_list:
        stu_list[qqid]=update_login_status_self(stu_list[qqid])
        return stu_list[qqid], True
    return None, False


def login_stu(qqid, username, password):
    """
    登录学生账号
    Args:
        qqid: QQ 号
        username: 学生账号
        password: 学生密码
    Return:
        Tuple: 登录是否成功
    """
    global stu_list
    if qqid in stu_list:
        return 2, stu_list[qqid].username
    try:
        stu = login_by_captcha(username, password)
    except Exception as e:
        logger.error(f"Failed to login student {username}: {e}")
        if Exception == LoginCaptchaError:
            return 4, None
        return 1, None
    stu_list = load_cache("stu_list")
    for qqid_, stu_ in stu_list.items():
        if stu_.id == stu.id:
            return 3, qqid_
    stu_list[qqid] = stu
    save_cache("stu_list", stu_list)
    return 0, None


def logout_stu(qqid):
    """
    登出学生账号
    Args:
        qqid: QQ 号
    Return:
        str: 学生账号
        bool: 登出是否成功
    """
    global stu_list
    stu_list = load_cache("stu_list")
    if qqid in stu_list:
        username = stu_list[qqid].username
        del stu_list[qqid]
        save_cache("stu_list", stu_list)
        return username, True
    return None, False


def get_user_info(qqid):
    """
    获得用户详细信息
    Args:
        qqid: QQ 号
    Return:
        str: 用户详细信息
    """
    stu = StuPerson(stu_list.get(qqid))
    return f"已登录的学生账号：{stu.name}({stu.id})"


def get_homeworks(qqid, finish=False):
    stu, status = stu_list.get(qqid)
    if not status:
        return None
    hws = stu.get_homeworks(20, finish, "-1", 0)
    result = [{"number": i, "id": homework.id, "title": homework.title} for i, homework in enumerate(hws)]
    return json.dumps(result)


def get_homework_answer(qqid, ids=0, finish=False):
    stu, status = stu_list.get(qqid)
    if not status:
        return None
    hws = stu.get_homeworks(20, finish, "-1", 0)
    hw = stu.get_homework_answer(hws[ids])

    result = [{"number": i, "title": now.title, "content": now.content} for i, now in enumerate(hw) if
              now.content != '']
    return json.dumps(result)


def get_classmates(qqid):
    stu, status = get_user(qqid)
    if not status:
        return None
    classmates = stu.get_classmates()
    result = [{"id": stud.id, "name": stud.name} for stud in classmates]
    return json.dumps(result)


def get_exams(qqid):
    stu, status = get_user(qqid)
    if not status:
        return None
    exams = stu.get_exams()
    returns = ""
    for i, exam in enumerate(exams):
        if i >= 10:
            break
        returns += f"{exam.name}: {exam.id}\n"
    return returns


def get_rank_by_stu_code(qqid, exam_id):
    """通过 stu_code 获得排名"""
    stu, status = get_user(qqid)
    if not status:
        return None
    stu_school = stu_list[qqid].clazz.school.id
    global tch_list
    if stu_school not in tch_list:
        raise FailedGetTeacherAccountError

    # Refactor: get_exam_all_rank
    global exam_scores
    exam_scores = load_cache("exam_scores")
    if exam_id not in exam_scores:
        tch_list[stu_school] = update_login_status_self(tch_list[stu_school])
        tch = tch_list[stu_school]
        save_cache("tch_list", tch_list)
        exam_scores[exam_id] = get_exam_all_rank(tch, exam_id)
        save_cache("exam_scores", exam_scores)
    students_scores_list = exam_scores[exam_id]
    returns = ""
    logger.debug(f"students_scores_list: {students_scores_list}")
    for student in students_scores_list:
        # logger.debug(student.username)
        if student.user_id == stu.id:
            for subject in student.scores:
                returns += f"{subject}: {student.scores[subject].score} (班次 {student.scores[subject].classrank}" \
                           f"/校次 {student.scores[subject].schoolrank})\n"
            logger.debug(returns)
            return returns


def get_exam_rank(qqid, exam_id: str):
    """获得成绩单"""
    stu_school = stu_list[qqid].clazz.school.id
    global tch_list
    if stu_school not in tch_list:
        raise FailedGetTeacherAccountError
    tch_list[stu_school] = update_login_status_self(tch_list[stu_school])
    tch = tch_list[stu_school]
    save_cache("tch_list", tch_list)
    wb = Workbook()
    ws = wb.active
    subjects_list = get_exam_subjects(tch, exam_id)
    global exam_scores
    exam_scores = load_cache("exam_scores", "list")
    if exam_id in exam_scores:
        students_scores_list = exam_scores[exam_id]
    else:
        students_scores_list = get_exam_all_rank(tch, exam_id)
        exam_scores[exam_id] = students_scores_list
        save_cache("exam_scores", exam_scores)
    titles = ["姓名", "标签", "班级", "总分", "总分班次", "总分校次"]
    for subject_code in subjects_list:
        subject_name = subjects_list[subject_code]["name"]
        titles.extend([subject_name + "成绩", subject_name + "班次", subject_name + "校次"])
    ws.append(titles)
    for student in students_scores_list:
        row = [student.username, student.label, student.class_name,
               student.scores["总分"].score, student.scores["总分"].classrank, student.scores["总分"].schoolrank]
        for subject_code in subjects_list:
            subject_name = subjects_list[subject_code]["name"]
            row.extend([student.scores[subject_name].score, student.scores[subject_name].classrank,
                        student.scores[subject_name].schoolrank])
        ws.append(row)
    file_name = f"./.zx/cache/scores_{exam_id}_{time.time()}.xlsx"
    wb.save(file_name)
    return file_name


def get_answersheet_by_stuid(qqid, stu_id, examid):
    """通过 student_id 获取答题卡"""
    stu_school = stu_list[qqid].clazz.school.id
    global tch_list
    if stu_school not in tch_list:
        raise FailedGetTeacherAccountError
    tch_list[stu_school] = update_login_status_self(tch_list[stu_school])
    tch = tch_list[stu_school]
    save_cache("tch_list", tch_list)
    subject_list = get_exam_subjects(tch, examid)
    images = []
    for subject_code in subject_list:
        subject_id = subject_list[subject_code]["id"]
        file_name = f"./.zx/cache/answersheet_{subject_id}_{stu_id}.png"
        if not os.path.exists(file_name):
            try:
                image = process_answersheet(tch, subject_id, stu_id)
            except ZhixueError as e:
                logger.warning(f"Failed to get answersheet: {e}")
                continue
            image.save(file_name)
        images.append(file_name)
    return images


def get_answersheet_by_stuname(stu_name, qqid, examid):
    """通过 学生姓名 获取答题卡"""
    stu_school = stu_list[qqid].clazz.school.id
    global tch_list
    if stu_school not in tch_list:
        raise FailedGetTeacherAccountError
    tch_list[stu_school] = update_login_status_self(tch_list[stu_school])
    tch = tch_list[stu_school]
    save_cache("tch_list", tch_list)
    stu, status = get_user(qqid)
    if not status:
        return None
    stu_id = get_stuid_by_stuname(tch, examid, stu_name)
    return get_answersheet_by_stuid(qqid, stu_id, examid)


def get_answersheet_by_qqid(qqid, examid):
    """通过 QQ 号获取答题卡"""
    stu, status = get_user(qqid)
    if not status:
        return None
    return get_answersheet_by_stuid(qqid, stu.id, examid)


# def get_original_paper(qqid, exam_id, subj_id):
#     stu, status = stu_list.get(qqid)
#     if not status:
#         return None
#     teacher = login_teacher(USERNAME_TEACHER, PASSWORD_TEACHER)
#     stu_id = stu.id
#
#     exams = stu.get_exams()
#     exam = exams[exam_id]
#     subjects = stu.get_subjects(exam)
#
#     paper_saved = teacher.get_original_paper(stu_id, subjects[subj_id].id, "./tmp/1.html")
#     if paper_saved:
#         return send_from_directory(os.path.join('.', 'tmp'), '1.html', as_attachment=False)
#     else:
#         return jsonify({"error": "Failed to download the paper."})


# def get_hide_exams():
#     teacher = login_teacher(USERNAME_TEACHER, PASSWORD_TEACHER)
#     exams = get_all_exam_list(teacher)
#     result = [{"number": i, "exam": exam} for i, exam in enumerate(exams)]
#     return jsonify(result)


# def get_hide_exam_subjects():
#     exam_id = request.args.get('examid', default=0, type=int)
#     teacher = login_teacher(USERNAME_TEACHER, PASSWORD_TEACHER)
#     exams = get_all_exam_list(teacher)
#     data = exams[exam_id].split(",")[0].strip()
#     subjects = get_all_exam_subjects(teacher, data)
#     result = [{"number": i, "subject": subj} for i, subj in enumerate(subjects)]
#     return jsonify(result)


# def get_exam_answer():
#     exam_id = request.args.get('examid', default=0, type=int)
#     topic_id = request.args.get('topicid', default=0, type=int)
#     teacher = login_teacher(USERNAME_TEACHER, PASSWORD_TEACHER)
#     exams = get_all_exam_list(teacher)
#     data1 = exams[exam_id].split(",")[0].strip()
#     subjects = get_all_exam_subjects(teacher, data1)
#     data2 = subjects[topic_id].split(",")[0].strip()
#     answers = get_all_exam_answer(teacher, data2)
#     result = [{"number": i, "answer": answer} for i, answer in enumerate(answers)]
#     return jsonify(result)
