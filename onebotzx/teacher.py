import json
import re
from time import sleep
from typing import List

from loguru import logger
from zhixuewang.teacher import TeacherAccount

from answersheet import draw_answersheet
from models import ZhixueError


class Score:
    def __init__(self, name, score, classrank, schoolrank, subjectcode):
        self.name = name
        self.score = score
        self.classrank = classrank
        self.schoolrank = schoolrank
        self.subjectcode = subjectcode


class StudentScoreInfo:
    def __init__(self, username, user_id, label, class_name, all_score, class_rank, school_rank):
        self.username = username
        self.user_id = user_id
        self.label = label
        self.class_name = class_name
        self.scores = {"总分": Score("总分", all_score, class_rank, school_rank, -1)}

    def add_subject_score(self, subject_name, score, class_rank, school_rank, subject_code):
        self.scores[subject_name] = Score(subject_name, score, class_rank, school_rank, subject_code)


def get_all_exam_list(myaccount: TeacherAccount) -> List:
    """
    获得所有后台考试列表
    Return:
        List: 所有后台考试列表
    """
    myaccount.update_login_status()
    r = myaccount.get_session().post(
        "https://pt-ali-bj-re.zhixue.com/exam/examcenter/examlist/index",
        data={"gradeCode": "ALL",
              "examTypeCode": "ALL",
              "createRole": "-1",
              "pageIndex": "1",
              "queryAll": "0"
              },
        headers={"token": myaccount.get_token()},
    )
    data = r.json()["message"]
    data = json.loads(data)
    examslist = []
    for exams in data["examList"]:
        exams_id = exams["examId"]
        exams_name = exams["examName"]
        grade_name = exams["gradeName"]
        strrr = f"{exams_id}, {exams_name}, {grade_name}"
        examslist.append(strrr)
    return examslist


def get_all_exam_subjects(myaccount: TeacherAccount, examid: str) -> List:
    """
    获得指定后台考试学科列表
    Return:
        List: 指定后台考试学科列表
    """
    myaccount.update_login_status()
    r = myaccount.get_session().post(
        "https://pt-ali-bj-re.zhixue.com/exam/examcenter/getMarkingPaperProgressDetail",
        data={"examId": examid},
        headers={"token": myaccount.get_token()},
    )
    data = r.json()["message"]
    data = json.loads(data)
    subjectslist = []
    for exam_id in data.keys():
        subject_name = data[exam_id]["subjectName"]
        strrr = f"{exam_id}, {subject_name}"
        subjectslist.append(strrr)
    return subjectslist


def get_all_exam_answer(myaccount: TeacherAccount, subjectid: str) -> List:
    """
    获得指定后台考试学科答案
    Return:
        List: 指定后台考试学科答案
    """
    myaccount.update_login_status()
    r = myaccount.get_session().post(
        "https://pt-ali-bj-re.zhixue.com/exam/objectiveset/initSetting",
        data={"markingPaperId": subjectid},
        headers={"token": myaccount.get_token()},
    )
    data = json.loads(r.text)

    answerlist = []
    for problems in data["topicList"]:
        problem_id = problems["topicSort"]
        problem_answer = problems["standardAnswer"]
        strrr = f"{problem_id}: {problem_answer}"
        answerlist.append(strrr)
    return answerlist


def get_exam_subjects(myaccount: TeacherAccount, examid: str) -> dict:
    """
    获得指定考试学科列表
    Args:
        myaccount: 教师账号
        examid: 考试 ID
    Return:
        dict: 指定考试学科列表
    """
    r = myaccount.get_session().post(
        "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank",
        data={
            "examId": examid,
            "pageIndexInt": 1,
            "version": "V3",
        },
        headers={"token": myaccount.get_token()},
    )
    subjects = json.loads(r.json()["result"]["allSubjectTopicSetListJSON"])
    subjectslist = {}
    for subject in subjects:
        subjectslist[subject["subjectCode"]] = {"id": subject["topicSetId"], "name": subject["subjectName"]}
    return subjectslist


def get_school_rank_by_stu_code(myaccount: TeacherAccount, examid: str, stu_code: str) -> List:
    """
    根据 stu_code 获得学校排名
    Args:
        myaccount: 教师账号
        examid: 考试 ID
        stu_code: 准考证号
    Return:
        List: 每科学校排名
    """
    subjects = get_exam_subjects(myaccount, examid)
    r = myaccount.get_session().post(
        "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank",
        data={
            "examId": examid,
            "pageIndexInt": 1,
            "version": "V3",
            "searchValue": stu_code,
        },
        headers={"token": myaccount.get_token()},
    )
    data = r.json()["result"]["studentRank"][0]
    total_score = Score("总分", data["allScore"], data["classRank"], data["schoolRank"], -1)
    subject_scores = [total_score]
    score_info = data["scoreInfos"]
    for info in score_info:
        subject_code = info["subjectCode"]
        subject_name = subjects[subject_code]["name"]
        subject_scores.append(Score(subject_name, info["score"], info["classRank"], info["schoolRank"], subject_code))
    return subject_scores


def calc_rank(student_list):
    def parse_score(score_str):
        if isinstance(score_str, (int, float)):
            return float(score_str)

        score_str = str(score_str)

        # 提取数字
        if "剔除" in score_str:
            numbers = re.findall(r'-?\d+\.?\d*', score_str)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    return -1
            return -1

        # 直接转换
        try:
            return float(score_str)
        except (ValueError, TypeError):
            return -1

    # 按科目分组
    subject_scores = {}
    for student in student_list:
        for subject_name, score_obj in student.scores.items():
            if subject_name not in subject_scores:
                subject_scores[subject_name] = []
            subject_scores[subject_name].append((student, score_obj))

    for subject_name, scores in subject_scores.items():
        # 按班级分组
        class_groups = {}
        for student, score_obj in scores:
            if student.class_name not in class_groups:
                class_groups[student.class_name] = []
            class_groups[student.class_name].append((student, score_obj))

        # 计算年级排名
        sorted_scores = sorted(scores, key=lambda x: parse_score(x[1].score), reverse=True)
        current_rank = 1
        prev_score = None
        for i, (student, score_obj) in enumerate(sorted_scores):
            current_score = parse_score(score_obj.score)
            if current_score == -1:
                score_obj.schoolrank = len(sorted_scores)
            else:
                if prev_score is not None and current_score != prev_score:
                    current_rank = i + 1
                score_obj.schoolrank = current_rank
            prev_score = current_score

        # 计算班级排名
        for class_name, class_scores in class_groups.items():
            sorted_class_scores = sorted(class_scores, key=lambda x: parse_score(x[1].score), reverse=True)
            current_rank = 1
            prev_score = None
            for i, (student, score_obj) in enumerate(sorted_class_scores):
                current_score = parse_score(score_obj.score)
                if current_score == -1:
                    score_obj.classrank = len(sorted_class_scores)
                else:
                    if prev_score is not None and current_score != prev_score:
                        current_rank = i + 1
                    score_obj.classrank = current_rank
                prev_score = current_score


def get_exam_all_rank(myaccount: TeacherAccount, examid: str) -> List:
    """
    获得全部成绩单
    Args:
        myaccount: 教师账号
        examid: 考试 ID
    Return:
        List: 成绩单
    """
    logger.info(f"Getting exam data: {examid}")
    r = myaccount.get_session().post(
        "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank",
        data={
            "examId": examid,
            "pageIndexInt": 1,
            "version": "V3",
        },
        headers={"token": myaccount.get_token()},
    )
    pages = r.json()["result"]["paperInfo"]["totalPage"]
    subjects = get_exam_subjects(myaccount, examid)
    students_list = []
    need_calc_rank = False
    for page in range(1, pages + 1):
        r = myaccount.get_session().post(
            "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank",
            data={
                "examId": examid,
                "pageIndexInt": page,
            }
        )
        data = r.json()["result"]
        for student in data["studentRank"]:
            student_info = StudentScoreInfo(student["userName"], student["userId"], student["studentLabel"],
                                            student["className"], student["allScore"], student["classRank"],
                                            student["schoolRank"])
            if "-" in student["schoolRank"] or "-" in student["classRank"]:
                need_calc_rank = True
            for score_info in student["scoreInfos"]:
                subject_name = subjects[score_info["subjectCode"]]["name"]
                student_info.add_subject_score(subject_name, score_info["score"], score_info["classRank"],
                                               score_info["schoolRank"], score_info["subjectCode"])
            students_list.append(student_info)
        sleep(0.5)
    if need_calc_rank:
        calc_rank(students_list)
    return students_list


def get_answersheet_data(myaccount: TeacherAccount, subjectid: str, stuid: str):  # FIXME: 某些答题卡数据格式不同(统考语文)
    """
    获取答题卡数据
    Args:
        myaccount: 教师账号
        subjectid: 学科 ID
        stuid: 学生 ID
    Return:
        tuple: 题号对应情况, 每页位置信息, 客观题答案, 作答及批改详情, 原卷链接, 纸张类型
    """
    r = myaccount.get_session().post(
        "https://www.zhixue.com/api-classreport/class/student/getNewCheckSheet/",
        data={
            "topicSetId": subjectid,
            "userId": stuid,
        },
        headers={"token": myaccount.get_token()},
    )

    try:
        data = r.json()["result"]
        data["sheetDatas"] = json.loads(data["sheetDatas"])
    except:
        raise ZhixueError(r.text)

    topic_mapping = data["markingTopicDetail"]  # 题号对应情况
    page_positions = {}  # 每页位置信息
    page_index_origin = 0
    for page in data["sheetDatas"]["answerSheetLocationDTO"]["pageSheets"]:
        page_index = page["pageIndex"]
        page_positions[page_index] = []
        for section in page["sections"]:
            out_left = section["contents"]["position"]["left"]
            out_top = section["contents"]["position"]["top"]
            flag = False
            use_outside_position = False
            for content in section["contents"]["branch"]:
                position = content["position"]
                if position == "":
                    use_outside_position = True
                    break
                if (flag or position["left"] <= 0 or position["top"] <= 0 or position["left"] < out_left or
                        position["top"] < out_top):
                    position["left"] += out_left
                    position["top"] += out_top
                    flag = True
                page_positions[page_index].append({
                    "height": position["height"],
                    "left": position["left"],
                    "top": position["top"],
                    "width": position["width"],
                    "ixList": content["ixList"]
                })
            if use_outside_position:
                page_index = page_index_origin
                if page_index not in page_positions:
                    page_positions[page_index] = []
                position = section["contents"]["position"]
                if (position["left"] <= 0 or position["top"] <= 0 or position["left"] < out_left or
                        position["top"] < out_top):
                    position["left"] += out_left
                    position["top"] += out_top
                page_positions[page_index].append({
                    "height": position["height"],
                    "left": position["left"],
                    "top": position["top"],
                    "width": position["width"],
                    "ixList": section["contents"]["branch"][0]["ixList"]
                })
                # logger.debug(f"Page {page_index}: {page_positions[page_index]}")
        page_index_origin +=1
    # 客观题答案
    objective_answer = {}
    for item in data["objectAnswer"]:
        topic_sort = item["topicSort"]
        objective_answer[topic_sort] = {
            "answer": item["answer"],
            "standardAnswer": item["standardAnswer"]
        }

    # 作答及批改详情（所有题目）
    answer_details = {}
    for record in data["sheetDatas"]["userAnswerRecordDTO"]["answerRecordDetails"]:
        topic_number = record["topicNumber"]
        answer_details[topic_number] = {
            "answer": record["answer"],
            "score": record["score"],
            "standardScore": record["standardScore"],
            "subTopics": []
        }
        for subtopic in record.get("subTopics", []):
            answer_details[topic_number]["subTopics"].append({
                "subTopicIndex": subtopic["subTopicIndex"],
                "score": subtopic["score"],
                "teacherMarkingRecords": [{
                    "score": teacher["score"],
                    "teacherName": teacher.get("teacherName")
                } for teacher in subtopic.get("teacherMarkingRecords", [])]
            })

    sheet_images = data["sheetImages"]  # 原卷链接
    paper_type = json.loads(data["answerSheetLocation"])["paperType"]  # 纸张类型

    return topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type


def process_answersheet(myaccount: TeacherAccount, subjectid: str, stuid: str):
    """
    处理答题卡
    Args:
        myaccount: 教师账号
        subjectid: 学科 ID
        stuid: 学生 ID
    """
    try:
        topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type \
        = get_answersheet_data(myaccount, subjectid, stuid)
    except Exception as e:
        logger.error(f"Failed to get answersheet data: {e}")
        raise ZhixueError("Failed to get answersheet data")
    try:
        image = draw_answersheet(topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type)
    except Exception as e:
        logger.error(f"Failed to draw answersheet: {e}")
        raise ZhixueError("Failed to draw answersheet")
    return image


def get_stuid_by_stuname(myaccount: TeacherAccount, examid: str, stuname: str) -> str:  # XXX: 适配无法获取的情况
    """
    根据学生姓名和 examid 获取学生 ID
    Args:
        myaccount: 教师账号
        examid: 考试 ID
        stuname: 学生姓名
    Return:
        str: 学生 ID
    """
    r = myaccount.get_session().post(
        "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank/",
        data={
            "examId": examid,
            "searchValue": stuname,
        },
        # headers={"token": myaccount.get_token()},
    )
    if "<html" in r.text:
        logger.warning("Failed to get student id")
        raise ZhixueError("Failed to get student id")
    data = r.json()["result"]["studentRank"][0]["userId"] # TODO: 支持多个学生，进行选择
    return data
