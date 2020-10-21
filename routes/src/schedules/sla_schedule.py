import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text
from routes.src.utils import directory_files


def print_sla_line(
    f3x_data,
    md5_directory,
    line_number,
    sla_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    image_num=None,
):
    try:
        if sla_list:
            last_page_cnt = 4 if len(sla_list) % 4 == 0 else len(sla_list) % 4
            schedule_total = 0
            os.makedirs(md5_directory + "SL-A/" + line_number, exist_ok=True)
            la_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SL-A")

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

                page_start_index = page_num * 4
                if page_num + 1 == page_cnt:
                    last_page = True

                # This call prepares data to render on PDF
                build_la_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    schedule_page_dict,
                    sla_list,
                    memo_array,
                )

                page_subtotal = float(schedule_page_dict["pageSubtotal"])
                schedule_total += page_subtotal
                if page_cnt == page_num + 1:
                    schedule_page_dict["scheduleTotal"] = "{0:.2f}".format(
                        schedule_total
                    )
                schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                la_outfile = (
                    md5_directory
                    + "SL-A/"
                    + line_number
                    + "/page_"
                    + str(page_num)
                    + ".pdf"
                )
                pypdftk.fill_form(la_infile, schedule_page_dict, la_outfile)

                # Memo text changes
                memo_dict = {}
                if len(memo_array) >= 1:
                    current_page_num += 1
                    temp_memo_outfile = (
                        md5_directory + "SL-A/" + line_number + "/page_memo_temp.pdf"
                    )
                    memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                        "TEXT"
                    )
                    memo_outfile = (
                        md5_directory
                        + "SL-A/"
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
                    pypdftk.concat([la_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, la_outfile)

                    if len(memo_array) >= 3:
                        current_page_num += 1
                        memo_dict = {}
                        memo_outfile = (
                            md5_directory
                            + "SL-A/"
                            + line_number
                            + "/page_memo_"
                            + str(page_num)
                            + ".pdf"
                        )
                        memo_dict["scheduleName_1"] = memo_array[2]["scheduleName"]
                        memo_dict["memoDescription_1"] = memo_array[2][
                            "memoDescription"
                        ]
                        memo_dict["transactionId_1"] = memo_array[2]["transactionId"]
                        memo_dict["PAGESTR"] = (
                            "PAGE "
                            + str(current_page_num)
                            + " / "
                            + str(total_no_of_pages)
                        )

                        if image_num:
                            memo_dict["IMGNO"] = image_num
                            image_num += 1

                        if len(memo_array) >= 4:
                            memo_dict["scheduleName_2"] = memo_array[3]["scheduleName"]
                            memo_dict["memoDescription_2"] = memo_array[3][
                                "memoDescription"
                            ]
                            memo_dict["transactionId_2"] = memo_array[3][
                                "transactionId"
                            ]

                        # build page
                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([la_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, la_outfile)

            pypdftk.concat(
                directory_files(md5_directory + "SL-A/" + line_number + "/"),
                md5_directory + "SL-A/" + line_number + "/all_pages.pdf",
            )
            if path.isfile(md5_directory + "SL-A/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SL-A/all_pages.pdf",
                        md5_directory + "SL-A/" + line_number + "/all_pages.pdf",
                    ],
                    md5_directory + "SL-A/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SL-A/temp_all_pages.pdf",
                    md5_directory + "SL-A/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SL-A/" + line_number + "/all_pages.pdf",
                    md5_directory + "SL-A/all_pages.pdf",
                )

        return image_num
    except:
        traceback.print_exception(*sys.exc_info())


# This method builds data for individual LA page
def build_la_per_page_schedule_dict(
    last_page,
    transactions_in_page,
    page_start_index,
    schedule_page_dict,
    sla_schedules,
    memo_array,
):
    page_subtotal = 0

    try:
        if not last_page:
            transactions_in_page = 4

        for index in range(transactions_in_page):
            schedule_dict = sla_schedules[page_start_index + index]
            process_memo_text(schedule_dict, "SL", memo_array)
            if schedule_dict["memoCode"] != "X":
                page_subtotal += schedule_dict["contributionAmount"]
            build_contributor_la_name_date_dict(
                index + 1, page_start_index, schedule_dict, schedule_page_dict
            )

    except Exception as e:
        print("Error : " + e + " in Schedule SL_A process_la_line")
        raise e

    schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)


def build_contributor_la_name_date_dict(index, key, schedule_dict, schedule_page_dict):

    try:
        if schedule_dict.get("contributorLastName"):
            contributor_full_name = []
            contributor_full_name.append(schedule_dict.get("contributorLastName"))
            contributor_full_name.append(schedule_dict.get("contributorFirstName"))
            contributor_full_name.append(schedule_dict.get("contributorMiddleName"))
            contributor_full_name.append(schedule_dict.get("contributorPrefix"))
            contributor_full_name.append(schedule_dict.get("contributorSuffix"))

            # removing empty string if any
            contributor_full_name = list(filter(None, contributor_full_name))
            schedule_page_dict["contributorName_" + str(index)] = ",".join(
                map(str, contributor_full_name)
            )

            del schedule_dict["contributorLastName"]
            del schedule_dict["contributorFirstName"]
            del schedule_dict["contributorMiddleName"]
            del schedule_dict["contributorPrefix"]
            del schedule_dict["contributorSuffix"]
        elif schedule_dict.get("contributorOrgName"):
            schedule_page_dict["contributorName_" + str(index)] = schedule_dict[
                "contributorOrgName"
            ]
            del schedule_dict["contributorOrgName"]

        if schedule_dict.get("contributionDate"):
            date_array = schedule_dict["contributionDate"].split("/")
            schedule_page_dict["contributionDateMonth_" + str(index)] = date_array[0]
            schedule_page_dict["contributionDateDay_" + str(index)] = date_array[1]
            schedule_page_dict["contributionDateYear_" + str(index)] = date_array[2]
            del schedule_dict["contributionDate"]

        if schedule_dict.get("contributionAmount"):
            if schedule_dict["contributionAmount"] == "":
                schedule_dict["contributionAmount"] = 0.0
            schedule_page_dict["contributionAmount_" + str(index)] = "{0:.2f}".format(
                schedule_dict["contributionAmount"]
            )
            del schedule_dict["contributionAmount"]

        if schedule_dict.get("contributionAggregate"):
            if schedule_dict["contributionAggregate"] == "":
                schedule_dict["contributionAggregate"] = 0.0
            schedule_page_dict[
                "contributionAggregate_" + str(index)
            ] = "{0:.2f}".format(schedule_dict["contributionAggregate"])
            del schedule_dict["contributionAggregate"]

        for key in schedule_dict:
            if key != "lineNumber":
                schedule_page_dict[key + "_" + str(index)] = schedule_dict[key]
    except Exception as e:
        print(
            "Error at key: "
            + key
            + " in Schedule SL-A tranlaction: "
            + str(schedule_dict)
        )
        raise e
