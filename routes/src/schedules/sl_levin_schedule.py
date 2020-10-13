import os
import pypdftk
import re

from flask import current_app
from os import path
from routes.src.utils import directory_files


def print_sl_levin(
    f3x_data,
    md5_directory,
    levin_name,
    sl_list,
    page_cnt,
    start_page,
    last_page_cnt,
    total_no_of_pages,
    image_num=None,
):

    try:
        if sl_list:
            levin_name = str(levin_name)

            reg = re.compile("^[a-z0-9._A-Z]+$")
            reg = bool(reg.match(levin_name))
            p_levin_name = levin_name

            if reg is False:
                p_levin_name = re.sub("[^A-Za-z0-9]+", "", levin_name)
            p_levin_name = str(p_levin_name).replace(" ", "")

            start_page += 1
            # schedule_total = 0
            os.makedirs(md5_directory + "SL/" + p_levin_name, exist_ok=True)
            sl_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SL")

            for sl_page_no in range(page_cnt):
                last_page = False
                sl_schedule_page_dict = {}
                sl_schedule_page_dict["accountName"] = levin_name
                sl_schedule_page_dict["pageNo"] = start_page + sl_page_no
                sl_schedule_page_dict["totalPages"] = total_no_of_pages

                if image_num:
                    sl_schedule_page_dict["IMGNO"] = image_num
                    image_num += 1

                page_start_index = sl_page_no * 1
                if sl_page_no + 1 == page_cnt:
                    last_page = True

                build_sl_levin_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    sl_schedule_page_dict,
                    sl_list,
                )

                sl_schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                sl_outfile = md5_directory + "SL/" + p_levin_name + "/page.pdf"
                pypdftk.fill_form(sl_infile, sl_schedule_page_dict, sl_outfile)

            pypdftk.concat(
                directory_files(md5_directory + "SL/" + p_levin_name + "/"),
                md5_directory + "SL/" + p_levin_name + "/all_pages.pdf",
            )

            if path.isfile(md5_directory + "SL/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SL/all_pages.pdf",
                        md5_directory + "SL/" + p_levin_name + "/all_pages.pdf",
                    ],
                    md5_directory + "SL/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SL/temp_all_pages.pdf",
                    md5_directory + "SL/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SL/" + p_levin_name + "/all_pages.pdf",
                    md5_directory + "SL/all_pages.pdf",
                )

        return image_num
    except Exception as e:
        raise e


def build_sl_levin_per_page_schedule_dict(
    last_page,
    transactions_in_page,
    page_start_index,
    sl_levin_schedule_page_dict,
    sl_levin_schedules,
):
    page_subtotal = 0
    try:
        if not last_page:
            transactions_in_page = 1

        for index in range(transactions_in_page):
            sl_levin_schedule_dict = sl_levin_schedules[0]
            build_contributor_sl_levin_name_date_dict(
                index + 1,
                page_start_index,
                sl_levin_schedule_dict,
                sl_levin_schedule_page_dict,
            )
    except Exception as e:
        print("Error : " + e + " in Schedule SL process_sl_levin_line")
        raise e

    sl_levin_schedule_page_dict["pageSubtotal"] = "{0:.2f}".format(page_subtotal)
    return sl_levin_schedule_dict


def build_contributor_sl_levin_name_date_dict(
    index, key, sl_schedule_dict, sl_schedule_page_dict
):

    try:
        list_SL_convert_2_decimals = [
            "itemizedReceiptsFromPersons",
            "unitemizedReceiptsFromPersons",
            "totalReceiptsFromPersons",
            "otherReceipts",
            "totalReceipts",
            "voterRegistrationDisbursements",
            "voterIdDisbursements",
            "gotvDisbursements",
            "genericCampaignDisbursements",
            "totalSubDisbursements",
            "otherDisbursements",
            "totalDisbursements",
            "beginningCashOnHand",
            "receipts",
            "subtotal",
            "disbursements",
            "endingCashOnHand",
            "itemizedReceiptsFromPersonsYTD",
            "unitemizedReceiptsFromPersonsYTD",
            "totalReceiptsFromPersonsYTD",
            "otherReceiptsYTD",
            "totalReceiptsYTD",
            "voterRegistrationDisbursementsYTD",
            "voterIdDisbursementsYTD",
            "gotvDisbursementsYTD",
            "genericCampaignDisbursementsYTD",
            "totalSubDisbursementsYTD",
            "otherDisbursementsYTD",
            "totalDisbursementsYTD",
            "beginningCashOnHandYTD",
            "receiptsYTD",
            "subtotalYTD",
            "disbursementsYTD",
            "endingCashOnHandYTD",
        ]

        list_skip = [
            "accountName",
            "receipts",
            "disbursements",
            "subtotal",
            "receiptsYTD",
            "disbursementsYTD",
            "subtotalYTD",
        ]
        for key in sl_schedule_dict:

            if key == "receipts":
                sl_schedule_page_dict[key] = sl_schedule_dict["totalReceipts"]
            if key == "disbursements":
                sl_schedule_page_dict[key] = sl_schedule_dict["totalDisbursements"]
            if key == "subtotal":
                sl_schedule_page_dict[key] = (
                    sl_schedule_dict["totalReceipts"]
                    + sl_schedule_dict["beginningCashOnHand"]
                )
            if key == "receiptsYTD":
                sl_schedule_page_dict[key] = sl_schedule_dict["totalReceiptsYTD"]
            if key == "disbursementsYTD":
                sl_schedule_page_dict[key] = sl_schedule_dict["totalDisbursementsYTD"]
            if key == "subtotalYTD":
                sl_schedule_page_dict[key] = (
                    sl_schedule_dict["totalReceiptsYTD"]
                    + sl_schedule_dict["beginningCashOnHandYTD"]
                )

            if key not in list_skip:
                sl_schedule_page_dict[key] = sl_schedule_dict[key]

            if key in list_SL_convert_2_decimals:
                sl_schedule_page_dict[key] = "{0:.2f}".format(
                    sl_schedule_page_dict[key]
                )

    except Exception as e:
        print(
            "Error at key: "
            + key
            + " in Schedule SL tranlaction: "
            + str(sl_schedule_dict)
        )
        raise e
