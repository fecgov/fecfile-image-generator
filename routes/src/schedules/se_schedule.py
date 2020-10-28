import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text
from routes.src.utils import directory_files


def print_se_line(
    f3x_data,
    md5_directory,
    line_number,
    se_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    image_num=None,
):
    try:
        if se_list:
            last_page_cnt = 2 if len(se_list) % 2 == 0 else len(se_list) % 2
            schedule_total = 0
            os.makedirs(md5_directory + "SE/" + line_number, exist_ok=True)
            se_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SE")

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

                page_start_index = page_num * 2
                if page_num + 1 == page_cnt:
                    last_page = True

                # This call prepares data to render on PDF
                build_se_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    schedule_page_dict,
                    se_list,
                    memo_array,
                )

                schedule_total += float(schedule_page_dict["pageSubtotal"])

                if page_cnt == page_num + 1:
                    schedule_page_dict["pageTotal"] = "{0:.2f}".format(schedule_total)
                schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                schedule_page_dict["committeeId"] = f3x_data["committeeId"]

                # checking for signed date, it is only available for submitted reports
                # and adding in date signed and treasurer name for signed reports
                if len(f3x_data["dateSigned"]) > 0:
                    date_signed_array = f3x_data["dateSigned"].split("/")
                    schedule_page_dict["dateSignedMonth"] = date_signed_array[0]
                    schedule_page_dict["dateSignedDay"] = date_signed_array[1]
                    schedule_page_dict["dateSignedYear"] = date_signed_array[2]
                schedule_page_dict["completingName"] = f3x_data["treasurerName"]
                se_outfile = (
                    md5_directory
                    + "SE/"
                    + line_number
                    + "/page_"
                    + str(page_num)
                    + ".pdf"
                )
                pypdftk.fill_form(se_infile, schedule_page_dict, se_outfile)

                # Memo text changes
                memo_dict = {}
                if len(memo_array) >= 1:
                    current_page_num += 1

                    temp_memo_outfile = (
                        md5_directory + "SE/" + line_number + "/page_memo_temp.pdf"
                    )
                    memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                        "TEXT"
                    )
                    memo_outfile = (
                        md5_directory
                        + "SE/"
                        + line_number
                        + "/page_memo_"
                        + str(page_num)
                        + ".pdf"
                    )
                    memo_dict["scheduleName_1"] = memo_array[0]["scheduleName"]
                    memo_dict["memoDescription_1"] = memo_array[0]["memoDescription"]
                    memo_dict["transactionId_1"] = memo_array[0]["transactionId"]
                    memo_dict["PAGESTR"] = (
                        "PAGE " + str(current_page_num) + " / " + str(total_no_of_pages)
                    )

                    if image_num:
                        memo_dict["IMGNO"] = image_num
                        image_num += 1

                    if len(memo_array) >= 2:
                        memo_dict["scheduleName_2"] = memo_array[1]["scheduleName"]
                        memo_dict["memoDescription_2"] = memo_array[1][
                            "memoDescription"
                        ]
                        memo_dict["transactionId_2"] = memo_array[1]["transactionId"]

                    # build page
                    pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                    pypdftk.concat([se_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, se_outfile)

            pypdftk.concat(
                directory_files(md5_directory + "SE/" + line_number + "/"),
                md5_directory + "SE/" + line_number + "/all_pages.pdf",
            )

            if path.isfile(md5_directory + "SE/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SE/all_pages.pdf",
                        md5_directory + "SE/" + line_number + "/all_pages.pdf",
                    ],
                    md5_directory + "SE/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SE/temp_all_pages.pdf",
                    md5_directory + "SE/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SE/" + line_number + "/all_pages.pdf",
                    md5_directory + "SE/all_pages.pdf",
                )
        return current_page_num, image_num
    except:
        traceback.print_exception(*sys.exc_info())


# This method builds data for individual SE page
def build_se_per_page_schedule_dict(
    last_page,
    transactions_in_page,
    page_start_index,
    schedule_page_dict,
    se_schedules,
    memo_array,
):
    page_subtotal = 0
    if not last_page:
        transactions_in_page = 2

    for index in range(transactions_in_page):
        schedule_dict = se_schedules[page_start_index + index]
        process_memo_text(schedule_dict, "SE", memo_array)
        if schedule_dict.get("memoCode") != "X":
            page_subtotal += schedule_dict.get("expenditureAmount", 0)
        for key in se_schedules[page_start_index]:
            build_se_name_date_dict(index + 1, key, schedule_dict, schedule_page_dict)

    schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)


def build_se_name_date_dict(index, key, schedule_dict, schedule_page_dict):
    try:
        if not schedule_dict.get(key):
            schedule_dict[key] = ""

        name_list = ["LastName", "FirstName", "MiddleName", "Prefix", "Suffix"]

        if schedule_dict.get("payeeLastName"):
            name = ""
            for item in name_list:
                item = "payee" + item
                if schedule_dict.get(item):
                    name += schedule_dict.get(item) + " "
            schedule_page_dict["payeeName_" + str(index)] = name[:-1]

        elif schedule_dict.get("payeeOrganizationName"):
            schedule_page_dict["payeeName_" + str(index)] = schedule_dict[
                "payeeOrganizationName"
            ]

        if schedule_dict.get("candidateLastName"):
            name = ""
            for item in name_list:
                item = "candidate" + item
                if schedule_dict.get(item):
                    name += schedule_dict.get(item) + " "
            schedule_page_dict["candidateName_" + str(index)] = name[:-1]

        if schedule_dict.get("completingLastName"):
            name = ""
            for item in name_list:
                item = "completing" + item
                if schedule_dict.get(item):
                    name += schedule_dict.get(item) + " "
            schedule_page_dict["completingName_" + str(index)] = name[:-1]

        if (key == "disbursementDate" and len(schedule_dict[key])) > 0:
            date_array = schedule_dict[key].split("/")
            schedule_page_dict["disbursementDateMonth_" + str(index)] = date_array[0]
            schedule_page_dict["disbursementDateDay_" + str(index)] = date_array[1]
            schedule_page_dict["disbursementDateYear_" + str(index)] = date_array[2]

        if (key == "dateSigned" and len(schedule_dict[key])) > 0:
            date_array = schedule_dict[key].split("/")
            schedule_page_dict["dateSignedMonth_" + str(index)] = date_array[0]
            schedule_page_dict["dateSignedDay_" + str(index)] = date_array[1]
            schedule_page_dict["dateSignedYear_" + str(index)] = date_array[2]

        if key == "electionCode":
            if schedule_dict[key][0] in ["P", "G"]:
                schedule_page_dict["electionType_" + str(index)] = schedule_dict[key][
                    0:1
                ]
            else:
                schedule_page_dict["electionType_" + str(index)] = "O"
            schedule_page_dict["electionYear_" + str(index)] = schedule_dict[key][1::]

        if (key == "disseminationDate" and len(schedule_dict[key])) > 0:
            date_array = schedule_dict[key].split("/")
            schedule_page_dict["disseminationDateMonth_" + str(index)] = date_array[0]
            schedule_page_dict["disseminationDateDay_" + str(index)] = date_array[1]
            schedule_page_dict["disseminationDateYear_" + str(index)] = date_array[2]
        else:
            if key == "expenditureAmount" or key == "calendarYTDPerElectionForOffice":
                schedule_page_dict[key + "_" + str(index)] = (
                    "{0:.2f}".format(schedule_dict[key]) if schedule_dict[key] else 0.0
                )
            else:
                schedule_page_dict[key + "_" + str(index)] = schedule_dict[key]
    except Exception as e:
        print(
            "Error at key: " + key + " in Schedule E transaction: " + str(schedule_dict)
        )
        raise e
