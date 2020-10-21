import os
import pypdftk

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text, build_memo_page
from routes.src.utils import directory_files


# This method is invoked for each SB line number, it builds PDF for line numbers
def print_sb_line(
    f3x_data,
    md5_directory,
    line_number,
    sb_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    image_num=None,
):

    if sb_list:
        last_page_cnt = 3 if len(sb_list) % 3 == 0 else len(sb_list) % 3
        schedule_total = 0
        os.makedirs(md5_directory + "SB/" + line_number, exist_ok=True)
        sb_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SB")

        for page_num in range(page_cnt):
            current_page_num += 1
            memo_array = []
            last_page = False
            schedule_page_dict = {}
            schedule_page_dict["lineNumber"] = line_number
            schedule_page_dict["pageNo"] = current_page_num
            schedule_page_dict["totalPages"] = total_no_of_pages

            if image_num:
                schedule_page_dict["IMGNO"] = image_num
                image_num += 1

            page_start_index = page_num * 3
            if page_num + 1 == page_cnt:
                last_page = True

            # This call prepares data to render on PDF
            build_sb_per_page_schedule_dict(
                last_page,
                last_page_cnt,
                page_start_index,
                schedule_page_dict,
                sb_list,
                memo_array,
            )

            schedule_total += float(schedule_page_dict["pageSubtotal"])

            if page_cnt == page_num + 1:
                schedule_page_dict["scheduleTotal"] = "{0:.2f}".format(schedule_total)
            schedule_page_dict["committeeName"] = f3x_data["committeeName"]
            sb_outfile = (
                md5_directory + "SB/" + line_number + "/page_" + str(page_num) + ".pdf"
            )
            pypdftk.fill_form(sb_infile, schedule_page_dict, sb_outfile)

            # Memo text changes and build memo pages and return updated current_page_num
            current_page_num, image_num = build_memo_page(
                memo_array,
                md5_directory,
                line_number,
                current_page_num,
                page_num,
                total_no_of_pages,
                sb_outfile,
                name="SB",
                image_num=image_num,
            )

        pypdftk.concat(
            directory_files(md5_directory + "SB/" + line_number + "/"),
            md5_directory + "SB/" + line_number + "/all_pages.pdf",
        )
        if path.isfile(md5_directory + "SB/all_pages.pdf"):
            pypdftk.concat(
                [
                    md5_directory + "SB/all_pages.pdf",
                    md5_directory + "SB/" + line_number + "/all_pages.pdf",
                ],
                md5_directory + "SB/temp_all_pages.pdf",
            )
            os.rename(
                md5_directory + "SB/temp_all_pages.pdf",
                md5_directory + "SB/all_pages.pdf",
            )
        else:
            os.rename(
                md5_directory + "SB/" + line_number + "/all_pages.pdf",
                md5_directory + "SB/all_pages.pdf",
            )

    return current_page_num, image_num


# This method builds data for individual SB page
def build_sb_per_page_schedule_dict(
    last_page,
    transactions_in_page,
    page_start_index,
    schedule_page_dict,
    schedules,
    memo_array,
):
    page_subtotal = 0
    if not last_page:
        transactions_in_page = 3

    for index in range(transactions_in_page):
        schedule_dict = schedules[page_start_index + index]
        process_memo_text(schedule_dict, "SB", memo_array)
        if schedule_dict["memoCode"] != "X":
            page_subtotal += schedule_dict["expenditureAmount"]
        for key in schedules[page_start_index]:
            build_payee_name_date_dict(
                index + 1, key, schedule_dict, schedule_page_dict
            )

    schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)
    # return schedule_dict


def build_payee_name_date_dict(index, key, schedule_dict, schedule_page_dict):
    try:
        if not schedule_dict.get(key):
            schedule_dict[key] = ""

        if schedule_dict.get("payeeLastName"):
            payee_full_name = []
            payee_full_name.append(schedule_dict.get("payeeLastName"))
            payee_full_name.append(schedule_dict.get("payeeFirstName"))
            payee_full_name.append(schedule_dict.get("payeeMiddleName"))
            payee_full_name.append(schedule_dict.get("payeePrefix"))
            payee_full_name.append(schedule_dict.get("payeeSuffix"))

            # removing empty string from payee_full_name if any
            payee_full_name = list(filter(None, payee_full_name))
            schedule_page_dict["payeeName_" + str(index)] = ",".join(
                map(str, payee_full_name)
            )

        elif schedule_dict.get("payeeOrganizationName"):
            schedule_page_dict["payeeName_" + str(index)] = schedule_dict[
                "payeeOrganizationName"
            ]

        if schedule_dict.get("beneficiaryCandidateLastName"):
            beneficiaryCandidate_full_name = []
            beneficiaryCandidate_full_name.append(
                schedule_dict.get("beneficiaryCandidateLastName")
            )
            beneficiaryCandidate_full_name.append(
                schedule_dict.get("beneficiaryCandidateFirstName")
            )
            beneficiaryCandidate_full_name.append(
                schedule_dict.get("beneficiaryCandidateMiddleName")
            )
            beneficiaryCandidate_full_name.append(
                schedule_dict.get("beneficiaryCandidatePrefix")
            )
            beneficiaryCandidate_full_name.append(
                schedule_dict.get("beneficiaryCandidateSuffix")
            )

            # removing empty string from beneficiaryCandidate_full_name if any
            beneficiaryCandidate_full_name = list(
                filter(None, beneficiaryCandidate_full_name)
            )
            schedule_page_dict["beneficiaryName_" + str(index)] = ",".join(
                map(str, beneficiaryCandidate_full_name)
            )

        if key == "electionCode":
            if schedule_dict[key] and schedule_dict[key][0] in ["P", "G"]:
                schedule_page_dict["electionType_" + str(index)] = schedule_dict[key][
                    0:1
                ]
            else:
                schedule_page_dict["electionType_" + str(index)] = "O"
            schedule_page_dict["electionYear_" + str(index)] = schedule_dict[key][1::]

        if key == "expenditureDate":
            date_array = schedule_dict[key].split("/")
            schedule_page_dict["expenditureDateMonth_" + str(index)] = date_array[0]
            schedule_page_dict["expenditureDateDay_" + str(index)] = date_array[1]
            schedule_page_dict["expenditureDateYear_" + str(index)] = date_array[2]
        else:
            if key == "expenditureAmount" or key == "expenditureAggregate":
                schedule_page_dict[key + "_" + str(index)] = "{0:.2f}".format(
                    schedule_dict[key]
                )
            else:
                schedule_page_dict[key + "_" + str(index)] = schedule_dict[key]
    except Exception as e:
        print(
            "Error at key: " + key + " in Schedule B transaction: " + str(schedule_dict)
        )
        raise e
