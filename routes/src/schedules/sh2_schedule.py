import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path
from routes.src.utils import directory_files


def print_sh2_line(
    f3x_data,
    md5_directory,
    tran_type_ident,
    sh2_list,
    page_cnt,
    current_page_num,
    total_no_of_pages,
    image_num=None,
):
    try:
        if sh2_list:
            last_page_cnt = 6 if len(sh2_list) % 6 == 0 else len(sh2_list) % 6
            os.makedirs(md5_directory + "SH2/" + tran_type_ident, exist_ok=True)
            sh2_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SH2")

            for page_num in range(page_cnt):
                current_page_num += 1
                last_page = False
                schedule_page_dict = {}
                schedule_page_dict["pageNo"] = current_page_num
                schedule_page_dict["totalPages"] = total_no_of_pages

                if image_num:
                    schedule_page_dict["IMGNO"] = image_num
                    image_num += 1

                page_start_index = page_num * 6
                if page_num + 1 == page_cnt:
                    last_page = True

                # This call prepares data to render on PDF
                build_sh2_per_page_schedule_dict(
                    last_page,
                    last_page_cnt,
                    page_start_index,
                    schedule_page_dict,
                    sh2_list,
                )

                schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                sh2_outfile = md5_directory + "SH2/" + tran_type_ident + "/page.pdf"
                pypdftk.fill_form(sh2_infile, schedule_page_dict, sh2_outfile)

            pypdftk.concat(
                directory_files(md5_directory + "SH2/" + tran_type_ident + "/"),
                md5_directory + "SH2/" + tran_type_ident + "/all_pages.pdf",
            )
            if path.isfile(md5_directory + "SH2/all_pages.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + "SH2/all_pages.pdf",
                        md5_directory + "SH2/" + tran_type_ident + "/all_pages.pdf",
                    ],
                    md5_directory + "SH2/temp_all_pages.pdf",
                )
                os.rename(
                    md5_directory + "SH2/temp_all_pages.pdf",
                    md5_directory + "SH2/all_pages.pdf",
                )
            else:
                os.rename(
                    md5_directory + "SH2/" + tran_type_ident + "/all_pages.pdf",
                    md5_directory + "SH2/all_pages.pdf",
                )

        return image_num
    except:
        traceback.print_exception(*sys.exc_info())


def build_sh2_per_page_schedule_dict(
    last_page, transactions_in_page, page_start_index, schedule_page_dict, sh2_schedules
):
    if not last_page:
        transactions_in_page = 6

    for index in range(transactions_in_page):
        schedule_dict = sh2_schedules[page_start_index + index]

        for key in sh2_schedules[page_start_index]:
            build_sh2_info_dict(index + 1, key, schedule_dict, schedule_page_dict)


def build_sh2_info_dict(index, key, schedule_dict, schedule_page_dict):

    try:
        for key in schedule_dict:
            if key in ["fundraising", "directCandidateSupport"]:
                if key == 'fundraising' and schedule_dict[key]:
                    schedule_dict[key] = 'f'
                if key == 'directCandidateSupport' and schedule_dict[key]:
                    schedule_dict[key] = 'd'
                schedule_dict[key] = schedule_dict[key]

            if key in ["federalPercent", "nonFederalPercent"]:
                schedule_dict[key] = "{:.2f}".format(float(schedule_dict[key]))

            schedule_page_dict[key + "_" + str(index)] = schedule_dict[key]

    except Exception as e:
        print(
            "Error at key: "
            + key
            + " in Schedule SH2 transaction: "
            + str(schedule_dict)
        )
        raise e
