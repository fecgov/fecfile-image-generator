import os
import pypdftk

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text
from routes.src.utils import directory_files


def print_slb_line(
    f3x_data,
    md5_directory,
    line_number,
    slb_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    image_num=None,
):
    try:
        if slb_list:
            last_page_cnt = 5 if len(slb_list) % 5 == 0 else len(slb_list) % 5
            schedule_total = 0
            os.makedirs(md5_directory + "SL-B/" + line_number, exist_ok=True)
            slb_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SL-B")

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

                page_start_index = page_num * 5
                if page_num + 1 == page_cnt:
                    last_page = True

                # This call prepares data to render on PDF
                build_slb_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    schedule_page_dict,
                    slb_list,
                    memo_array,
                )

                page_subtotal = float(schedule_page_dict["pageSubtotal"])
                schedule_total += page_subtotal
                if page_cnt == (page_num + 1):
                    schedule_page_dict["scheduleTotal"] = "{0:.2f}".format(
                        schedule_total
                    )
                schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                slb_outfile = (
                    md5_directory
                    + "SL-B/"
                    + line_number
                    + "/page_"
                    + str(page_num)
                    + ".pdf"
                )
                pypdftk.fill_form(slb_infile, schedule_page_dict, slb_outfile)

                # Memo text changes
                if len(memo_array) >= 1:
                    current_page_num += 1
                    memo_dict = {}
                    temp_memo_outfile = (
                        md5_directory + "SL-B/" + line_number + "/page_memo_temp.pdf"
                    )
                    memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                        "TEXT"
                    )

                    memo_outfile = (
                        md5_directory
                        + "SL-B/"
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
                    pypdftk.concat([slb_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, slb_outfile)

                    if len(memo_array) >= 3:
                        current_page_num += 1
                        memo_dict = {}
                        memo_outfile = (
                            md5_directory
                            + "SL-B/"
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
                        pypdftk.concat([slb_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, slb_outfile)

                    if len(memo_array) >= 5:
                        current_page_num += 1
                        memo_dict = {}
                        memo_outfile = (
                            md5_directory
                            + "SL-B/"
                            + line_number
                            + "/page_memo_"
                            + str(page_num)
                            + ".pdf"
                        )
                        memo_dict["scheduleName_1"] = memo_array[4]["scheduleName"]
                        memo_dict["memoDescription_1"] = memo_array[4][
                            "memoDescription"
                        ]
                        memo_dict["transactionId_1"] = memo_array[4]["transactionId"]
                        memo_dict["PAGESTR"] = (
                            "PAGE "
                            + str(current_page_num)
                            + " / "
                            + str(total_no_of_pages)
                        )

                        if image_num:
                            memo_dict["IMGNO"] = image_num
                            image_num += 1

                        # build page
                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([slb_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, slb_outfile)

            pypdftk.concat(
                directory_files(md5_directory + "SL-B/" + line_number + "/"),
                md5_directory + "SL-B/" + line_number + "/all_pages.pdf",
            )
            if path.isfile(md5_directory + "SL-B/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SL-B/all_pages.pdf",
                        md5_directory + "SL-B/" + line_number + "/all_pages.pdf",
                    ],
                    md5_directory + "SL-B/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SL-B/temp_all_pages.pdf",
                    md5_directory + "SL-B/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SL-B/" + line_number + "/all_pages.pdf",
                    md5_directory + "SL-B/all_pages.pdf",
                )

        return image_num
    except Exception as e:
        return error("Error generating print preview, error message: " + str(e))


def build_slb_per_page_schedule_dict(
    last_page,
    transactions_in_page,
    page_start_index,
    schedule_page_dict,
    slb_schedules,
    memo_array,
):

    page_subtotal = 0
    if not last_page:
        transactions_in_page = 5

    for index in range(transactions_in_page):
        schedule_dict = slb_schedules[page_start_index + index]
        process_memo_text(schedule_dict, "SL", memo_array)
        if schedule_dict["memoCode"] != "X":
            page_subtotal += schedule_dict["expenditureAmount"]
        for key in slb_schedules[page_start_index]:
            build_slb_name_date_dict(index + 1, key, schedule_dict, schedule_page_dict)

    schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)


def build_slb_name_date_dict(index, key, schedule_dict, schedule_page_dict):
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

            # removing empty string if any
            payee_full_name = list(filter(None, payee_full_name))
            schedule_page_dict["payeeName_" + str(index)] = ",".join(
                map(str, payee_full_name)
            )

        elif schedule_dict.get("payeeOrganizationName"):
            schedule_page_dict["payeeName_" + str(index)] = schedule_dict[
                "payeeOrganizationName"
            ]

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
            "Error at key: "
            + key
            + " in Schedule-LB transaction: "
            + str(schedule_dict)
        )
        raise e
