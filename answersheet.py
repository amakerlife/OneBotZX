from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

from models import ZhixueError


def get_size(text, font):
    left, top, right, bottom = font.getbbox(text, "utf-8")
    width = right - left
    height = bottom - top
    return width, height


def check_multiple(student_answer_str, standard_answer_str):
    """
    Returns:
        0: 正确
        1: 少选
        2: 多选
    """
    student_answer = set(student_answer_str)
    standard_answer = set(standard_answer_str)
    if student_answer == standard_answer:
        return 0
    elif student_answer.issubset(standard_answer):
        return 1
    else:
        return 2


def vertical_concat(image_list):
    """
    将多个 Image 对象垂直拼接
    """
    widths, heights = zip(*(i.size for i in image_list))
    total_width = max(widths)
    total_height = sum(heights)

    new_im = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for im in image_list:
        new_im.paste(im, (0, y_offset))
        y_offset += im.size[1]

    return new_im


def draw_details(image, text, font, x, y, color, cnt):
    draw = ImageDraw.Draw(image)
    draw.text((x + 5, y + 10 + cnt), text, fill=color, font=font)
    cnt += 30
    return image, cnt


def draw_answersheet(topic_mapping, page_positions, objective_answer, answer_details, sheet_images, paper_type):
    images = []
    for i, image_url in enumerate(sheet_images):
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGB")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("msyh.ttc", 25, encoding="utf-8")

        image_width, image_height = image.size

        if paper_type == "A3":
            paper_width, paper_height = 420, 297
        elif paper_type == "A4":
            paper_width, paper_height = 210, 297
        else:
            raise ZhixueError("Unknown paper type")

        for position in page_positions[i]:
            # 计算矩形坐标
            left = position["left"] * image_width / paper_width
            top = position["top"] * image_height / paper_height
            right = left + position["width"] * image_width / paper_width
            bottom = top + position["height"] * image_height / paper_height
            problems = position["ixList"]

            # 绘制选择题每小题得分
            sum_score, standard_sum_score = 0, 0
            for j, problem in enumerate(problems):
                if problem in objective_answer:
                    if check_multiple(objective_answer[problem]["answer"],
                                      objective_answer[problem]["standardAnswer"]) == 0:
                        draw.text((left + 5, top + 10 + 27 * j),
                                  f"{topic_mapping.get(str(problem))}: {objective_answer[problem]['answer']}",
                                  fill="green", font=font)
                    elif check_multiple(objective_answer[problem]["answer"],
                                        objective_answer[problem]["standardAnswer"]) == 1:
                        draw.text((left + 5, top + 10 + 27 * j),                                 f"{topic_mapping.get(str(problem))}: {objective_answer[problem]['standardAnswer']}({objective_answer[problem]['answer']})",
                                  fill="darkorange", font=font)
                    else:
                        draw.text((left + 5, top + 10 + 27 * j),
                                  f"{topic_mapping.get(str(problem))}: {objective_answer[problem]['standardAnswer']}({objective_answer[problem]['answer']})",
                                  fill="red", font=font)
                    sum_score += answer_details[problem]["score"]
                    standard_sum_score += answer_details[problem]["standardScore"]

            # 绘制主观题各题目得分及阅卷老师
            cnt = 0
            for topic_number, details in answer_details.items():
                if topic_number in problems and topic_number not in objective_answer:
                    sum_score += details["score"]
                    standard_sum_score += details["standardScore"]
                    if details['score'] == details['standardScore']:
                        image, cnt = draw_details(image,
                                                  f"{topic_mapping.get(str(topic_number))}: 得分: {details['score']}/{details['standardScore']}",
                                                  font, left, top, "green", cnt)
                    elif details['score'] == 0:
                        image, cnt = draw_details(image,
                                                  f"{topic_mapping.get(str(topic_number))}: 得分: {details['score']}/{details['standardScore']}",
                                                  font, left, top, "red", cnt)
                    else:
                        image, cnt = draw_details(image,
                                                  f"{topic_mapping.get(str(topic_number))}: 得分: {details['score']}/{details['standardScore']}",
                                                  font, left, top, "darkorange", cnt)
                    if len(details["subTopics"]) > 1:
                        for subtopic in details["subTopics"]:
                            image, cnt = draw_details(image,
                                                      f"小题 {subtopic['subTopicIndex']}: 得分: {subtopic['score']}",
                                                      font,
                                                      left,
                                                      top, "blue", cnt)
                            for record in subtopic["teacherMarkingRecords"]:
                                teacher_name = record.get("teacherName", "未知教师")
                                image, cnt = draw_details(image, f"{teacher_name} 打分: {record['score']}", font, left,
                                                          top,
                                                          "blue", cnt)
                    elif details["subTopics"]:
                        subtopic = details["subTopics"][0]
                        for record in subtopic["teacherMarkingRecords"]:
                            teacher_name = record.get("teacherName", "未知教师")
                            image, cnt = draw_details(image, f"{teacher_name} 打分: {record['score']}", font, left, top,
                                                      "blue", cnt)

            # 绘制区域边框及总分
            text_width, text_height = get_size(f"{sum_score}/{standard_sum_score}", font)
            if sum_score == standard_sum_score:
                draw.rectangle([left, top, right, bottom], outline="green", width=5)
                draw.text((right - 5 - text_width, bottom - 10 - text_height),
                          f"{sum_score}/{standard_sum_score}", fill="green", font=font)
            elif sum_score == 0:
                draw.rectangle([left, top, right, bottom], outline="red", width=5)
                draw.text((right - 5 - text_width, bottom - 10 - text_height),
                          f"{sum_score}/{standard_sum_score}", fill="red", font=font)
            else:
                draw.rectangle([left, top, right, bottom], outline="orange", width=5)
                draw.text((right - 5 - text_width, bottom - 10 - text_height),
                          f"{sum_score}/{standard_sum_score}", fill="darkorange", font=font)

        images.append(image)
    all_image = vertical_concat(images)

    # 计算总分
    all_score = 0
    standard_all_score = 0
    for details in answer_details.values():
        all_score += details["score"]
        standard_all_score += details["standardScore"]

    draw = ImageDraw.Draw(all_image)
    font = ImageFont.truetype("msyh.ttc", 50, encoding="utf-8")
    draw.text((10, 10), f"{all_score}/{standard_all_score}", fill="red", font=font)
    draw.text((10, 70), f"本答题卡数据仅供参考，具体以智学网分数为准", fill="blue", font=font)
    return all_image
