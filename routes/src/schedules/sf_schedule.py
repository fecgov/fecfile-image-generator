import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text, build_memo_page
from routes.src.utils import directory_files


def print_sf_line(
    f3x_data,
    md5_directory,
    line_number,
    sf_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    cord_name=None,
    image_num=None,
):
    try:
        if sf_list:
            last_page_cnt = 3 if len(sf_list) % 3 == 0 else len(sf_list) % 3
            schedule_total = 0
            os.makedirs(md5_directory + "SF/" + cord_name, exist_ok=True)
            sf_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SF")

            for page_num in range(page_cnt):
                current_page_num += 1
                page_subtotal = 0
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
                build_sf_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    schedule_page_dict,
                    sf_list,
                    memo_array,
                )

                page_subtotal = float(schedule_page_dict["pageSubtotal"])
                schedule_page_dict["pageSubTotal"] = "{0:.2f}".format(page_subtotal)
                schedule_total += page_subtotal

                if page_cnt == page_num + 1:
                    schedule_page_dict["pageTotal"] = "{0:.2f}".format(schedule_total)

                schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                sf_outfile = (
                    md5_directory
                    + "SF/"
                    + cord_name
                    + "/page_"
                    + str(page_num)
                    + ".pdf"
                )

                pypdftk.fill_form(sf_infile, schedule_page_dict, sf_outfile)

                # Memo text changes and build memo pages and return updated current_page_num
                current_page_num, image_num = build_memo_page(
                    memo_array,
                    md5_directory,
                    cord_name,
                    current_page_num,
                    page_num,
                    total_no_of_pages,
                    sf_outfile,
                    name="SF",
                    image_num=image_num,
                )

            pypdftk.concat(
                directory_files(md5_directory + "SF/" + cord_name + "/"),
                md5_directory + "SF/" + cord_name + "/all_pages.pdf",
            )
            if path.isfile(md5_directory + "SF/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SF/all_pages.pdf",
                        md5_directory + "SF/" + cord_name + "/all_pages.pdf",
                    ],
                    md5_directory + "SF/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SF/temp_all_pages.pdf",
                    md5_directory + "SF/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SF/" + cord_name + "/all_pages.pdf",
                    md5_directory + "SF/all_pages.pdf",
                )

        return image_num
    except:
        traceback.print_exception(*sys.exc_info())


# This method builds data for individual SF page
def build_sf_per_page_schedule_dict(
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
        process_memo_text(schedule_dict, "SF", memo_array)
        if schedule_dict["memoCode"] != "X":
            page_subtotal += schedule_dict["expenditureAmount"]
        for key in schedules[page_start_index]:
            build_payee_sf_name_date_dict(
                index + 1, key, schedule_dict, schedule_page_dict
            )

    schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)
    return schedule_dict


def build_payee_sf_name_date_dict(index, key, schedule_dict, schedule_page_dict):
    try:
        if not schedule_dict.get(key):
            schedule_dict[key] = ""

        if schedule_dict.get("designatingCommitteeName"):
            schedule_page_dict["designatingCommitteeName"] = schedule_dict[
                "designatingCommitteeName"
            ]

        if schedule_dict.get("subordinateCommitteeName"):
            schedule_page_dict["subordinateCommitteeName"] = schedule_dict[
                "subordinateCommitteeName"
            ]
            schedule_page_dict["subordinateCommitteeStreet1"] = schedule_dict[
                "subordinateCommitteeStreet1"
            ]
            schedule_page_dict["subordinateCommitteeStreet2"] = schedule_dict[
                "subordinateCommitteeStreet2"
            ]
            schedule_page_dict["subordinateCommitteeCity"] = schedule_dict[
                "subordinateCommitteeCity"
            ]
            schedule_page_dict["subordinateCommitteeState"] = schedule_dict[
                "subordinateCommitteeState"
            ]
            schedule_page_dict["subordinateCommitteeZipCode"] = schedule_dict[
                "subordinateCommitteeZipCode"
            ]

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
        elif schedule_dict.get("designatingCommitteeName"):
            schedule_page_dict["payeeName_" + str(index)] = schedule_dict[
                "designatingCommitteeName"
            ]

        if schedule_dict.get("payeeCandidateLastName"):
            name = ""
            for item in name_list:
                item = "payeeCandidate" + item
                if schedule_dict.get(item):
                    name += schedule_dict.get(item) + " "
            schedule_page_dict["payeeCandidateName_" + str(index)] = name[:-1]

        if key == "expenditureDate" and schedule_dict["expenditureDate"] not in [
            "none",
            "null",
            " ",
            "",
        ]:
            date_array = schedule_dict[key].split("/")
            schedule_page_dict["expenditureDateMonth_" + str(index)] = date_array[0]
            schedule_page_dict["expenditureDateDay_" + str(index)] = date_array[1]
            schedule_page_dict["expenditureDateYear_" + str(index)] = date_array[2]
        else:
            if key == "expenditureAmount" or key == "aggregateGeneralElectionExpended":
                schedule_page_dict[key + "_" + str(index)] = (
                    "{0:.2f}".format(schedule_dict[key]) if schedule_dict[key] else 0.0
                )
            else:
                schedule_page_dict[key + "_" + str(index)] = schedule_dict[key]
    except Exception as e:
        print(
            "Error at key: " + key + " in Schedule F transaction: " + str(schedule_dict)
        )
        raise e
