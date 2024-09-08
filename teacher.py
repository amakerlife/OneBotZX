import json
from typing import List
from time import sleep
from venv import logger

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
    def __init__(self, username, label, class_name, all_score, class_rank, school_rank):
        self.username = username
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


def get_exam_all_rank(myaccount: TeacherAccount, examid: str) -> List:
    """
    获得全部成绩单
    Args:
        myaccount: 教师账号
        examid: 考试 ID
    Return:
        List: 成绩单
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
    pages = r.json()["result"]["paperInfo"]["totalPage"]
    subjects = get_exam_subjects(myaccount, examid)
    students_list = []
    for page in range(1, pages + 1):
        r = myaccount.get_session().post(
            "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank",
            data={
                "examId": examid,
                "pageIndexInt": page,
                "version": "V3",
            },
            headers={"token": myaccount.get_token()},
        )
        data = r.json()["result"]
        for student in data["studentRank"]:
            student_info = StudentScoreInfo(student["userName"], student["studentLabel"], student["className"],
                                            student["allScore"], student["classRank"], student["schoolRank"])
            for score_info in student["scoreInfos"]:
                subject_name = subjects[score_info["subjectCode"]]["name"]
                student_info.add_subject_score(subject_name, score_info["score"], score_info["classRank"],
                                               score_info["schoolRank"], score_info["subjectCode"])
            students_list.append(student_info)
        sleep(0.5)
        # logger.debug(f"Page {page}/{pages} done")
    return students_list


def get_answersheet_data(myaccount: TeacherAccount, subjectid: str, stuid: str):  # FIXME: 某些答题卡数据格式不同
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
    )

    try:
        data = r.json()["result"]
        data["sheetDatas"] = json.loads(data["sheetDatas"])
    except:
        raise ZhixueError(r.text)

    topic_mapping = data["markingTopicDetail"]  # 题号对应情况

    page_positions = {}  # 每页位置信息
    for page in data["sheetDatas"]["answerSheetLocationDTO"]["pageSheets"]:
        page_index = page["pageIndex"]
        page_positions[page_index] = []
        for section in page["sections"]:
            out_left = section["contents"]["position"]["left"]
            out_top = section["contents"]["position"]["top"]
            flag = False
            for content in section["contents"]["branch"]:
                position = content["position"]
                if position == "":
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
    topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type \
        = get_answersheet_data(myaccount, subjectid, stuid)
    image = draw_answersheet(topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type)
    return image


def get_stuid_by_stuname(myaccount: TeacherAccount, examid: str, stuname: str) -> str:  # XXX: 适配无法获取的情况
    """
    根据学生姓名、examid 和 classid 获取学生 ID
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
