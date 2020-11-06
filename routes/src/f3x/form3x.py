import flask
import boto3
import re
import os
import os.path
import pypdftk
import shutil
import sys
import traceback
import urllib.request

from collections import OrderedDict
from os import path
from flask import json
from flask import request, current_app
from flask_api import status
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject
from routes.src import tmoflask, utils, common, form
from routes.src.utils import md5_for_text, md5_for_file, directory_files, merge, error
from routes.src.f3x.helper import calculate_page_count, calculate_sh3_page_count, map_txn_img_num

# importing prcoess schedule
from routes.src.schedules.sa_schedule import print_sa_line
from routes.src.schedules.sb_schedule import print_sb_line
from routes.src.schedules.sc_schedule import print_sc_line
from routes.src.schedules.sc1_schedule import print_sc1_line
from routes.src.schedules.sd_schedule import print_sd_line
from routes.src.schedules.se_schedule import print_se_line
from routes.src.schedules.sf_schedule import print_sf_line
from routes.src.schedules.sh1_schedule import print_sh1_line
from routes.src.schedules.sh2_schedule import print_sh2_line
from routes.src.schedules.sh3_schedule import print_sh3_line
from routes.src.schedules.sh4_schedule import print_sh4_line
from routes.src.schedules.sh5_schedule import print_sh5_line
from routes.src.schedules.sh6_schedule import print_sh6_line
from routes.src.schedules.sl_levin_schedule import print_sl_levin
from routes.src.schedules.sla_schedule import print_sla_line
from routes.src.schedules.slb_schedule import print_slb_line

from routes.src.f3x.line_numbers import (
    process_sa_line_numbers,
    process_sf_line_numbers,
    process_sh_line_numbers,
    process_line_numbers,
)


# stamp_print is a flag that will be passed at the time of submitting a report.
def print_pdftk(stamp_print, paginate=False):
    # check if json_file_name is in the request
    try:
        if (paginate and "json_file_name" in request.json) or (
            not paginate and "json_file" in request.files
        ):

            if paginate and "json_file_name" in request.json:
                json_file_name = request.json.get("json_file_name")

                page_count = True if request.json.get("page_count") else False
                silent_print = True if request.json.get("silent_print") else False
                txn_img_num = None

                if paginate or silent_print:
                    txn_img_num = request.json.get("begin_image_num")

                    if not txn_img_num:
                        if flask.request.method == "POST":
                            envelope = common.get_return_envelope(
                                "false", "begin_image_num is missing from your request"
                            )
                            status_code = status.HTTP_400_BAD_REQUEST
                            return flask.jsonify(**envelope), status_code

                    filing_timestamp = request.json.get("filing_timestamp")

                # file_url = current_app.config["AWS_S3_FECFILE_COMPONENTS_DOMAIN"] + "/" + json_file_name + ".json"
                file_url = (
                    "https://dev-efile-repo.s3.amazonaws.com/"
                    + json_file_name
                    + ".json"
                )

                with urllib.request.urlopen(file_url) as url:
                    file_content = url.read().decode()

                # using md5_for_text as input is a url
                json_file_md5 = md5_for_text(file_content)
                f3x_json = json.loads(file_content)

            elif not paginate and "json_file" in request.files:
                json_file = request.files.get("json_file")
                page_count = (
                    True
                    if request.form.get("page_count")
                    and request.form.get("page_count").lower() in ["true", "1"]
                    else False
                )
                silent_print = (
                    True
                    if request.form.get("silent_print")
                    and request.form.get("silent_print").lower() in ["true", "1"]
                    else False
                )
                txn_img_num = None

                if silent_print:
                    txn_img_num = request.form.get("begin_image_num")

                    if not txn_img_num:
                        if flask.request.method == "POST":
                            envelope = common.get_return_envelope(
                                "false", "begin_image_num is missing from your request"
                            )
                            status_code = status.HTTP_400_BAD_REQUEST
                            return flask.jsonify(**envelope), status_code
                    txn_img_num = int(txn_img_num)

                    filing_timestamp = request.form.get("filing_timestamp")

                json_file_md5 = md5_for_file(json_file)
                json_file.stream.seek(0)

                # save json file as md5 file name
                json_file.save(
                    current_app.config["REQUEST_FILE_LOCATION"].format(json_file_md5)
                )

                # load json file
                f3x_json = json.load(
                    open(
                        current_app.config["REQUEST_FILE_LOCATION"].format(
                            json_file_md5
                        )
                    )
                )

            total_no_of_pages = 0
            page_no = 1

            schedule_dict = {
                "has_sa_schedules": [False, "SA"],
                "has_sb_schedules": [False, "SB"],
                "has_sc_schedules": [False, "SC"],
                "has_sd_schedules": [False, "SD"],
                "has_se_schedules": [False, "SE"],
                "has_sf_schedules": [False, "SF"],
                "has_sh1_schedules": [False, "SH1"],
                "has_sh2_schedules": [False, "SH2"],
                "has_sh3_schedules": [False, "SH3"],
                "has_sh4_schedules": [False, "SH4"],
                "has_sh5_schedules": [False, "SH5"],
                "has_sh6_schedules": [False, "SH6"],
                "has_sl_summary": [False, "SL"],
                "has_sla_schedules": [False, "SL-A"],
                "has_slb_schedules": [False, "SL-B"],
            }

            schedule_key_list = [
                "has_sa_schedules",
                "has_sb_schedules",
                "has_sc_schedules",
                "has_sd_schedules",
                "has_se_schedules",
                "has_sf_schedules",
                "has_sh1_schedules",
                "has_sh2_schedules",
                "has_sh3_schedules",
                "has_sh4_schedules",
                "has_sh5_schedules",
                "has_sh6_schedules",
                "has_sl_summary",
                "has_sla_schedules",
                "has_slb_schedules",
            ]

            # generate md5 for json file
            # FIXME: check if PDF already exist with md5, if exist return pdf instead of re-generating PDF file.

            md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(
                json_file_md5
            )

            # checking if server has already generated pdf for same json file
            # if os.path.isdir(md5_directory) and path.isfile(md5_directory + 'all_pages.pdf'):
            #     # push output file to AWS
            #     s3 = boto3.client('s3')
            #     s3.upload_file(md5_directory + 'all_pages.pdf',
            #                    current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
            #                    md5_directory + 'all_pages.pdf',
            #                    ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
            #     response = {
            #         'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5) + 'all_pages.pdf'
            #     }
            #
            #     # return response
            #     if flask.request.method == "POST":
            #         envelope = common.get_return_envelope(
            #             data=response
            #         )
            #         status_code = status.HTTP_201_CREATED
            #         return flask.jsonify(**envelope), status_code
            #

            if not page_count and not paginate:
                os.makedirs(md5_directory, exist_ok=True)

            infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("F3X")
            outfile = md5_directory + json_file_md5 + "_temp.pdf"

            # setting timestamp and imgno to empty as these needs to show up after submission
            if stamp_print != "stamp":
                f3x_json["FILING_TIMESTAMP"] = ""
                f3x_json["IMGNO"] = ""

            # read data from json file
            f3x_data = f3x_json["data"]

            # check if summary is present in fecDataFile
            f3x_summary = []
            if f3x_data.get("summary"):
                f3x_summary_temp = f3x_data["summary"]
                f3x_summary = {"cashOnHandYear": f3x_summary_temp["cashOnHandYear"]}
                # building colA_ and colB_ mapping data for PDF
                f3x_col_a = f3x_summary_temp["colA"]
                f3x_col_b = f3x_summary_temp["colB"]
                for key in f3x_col_a:
                    f3x_summary["colA_" + key] = "{0:.2f}".format(f3x_col_a[key])
                for key in f3x_col_b:
                    f3x_summary["colB_" + key] = "{0:.2f}".format(f3x_col_b[key])

            # split coverage start date and coverage end date to set month, day, and year
            coverage_start_date_array = f3x_data["coverageStartDate"].split("/")
            f3x_data["coverageStartDateMonth"] = coverage_start_date_array[0]
            f3x_data["coverageStartDateDay"] = coverage_start_date_array[1]
            f3x_data["coverageStartDateYear"] = coverage_start_date_array[2]

            coverage_end_date_array = f3x_data["coverageEndDate"].split("/")
            f3x_data["coverageEndDateMonth"] = coverage_end_date_array[0]
            f3x_data["coverageEndDateDay"] = coverage_end_date_array[1]
            f3x_data["coverageEndDateYear"] = coverage_end_date_array[2]

            # checking for signed date, it is only available for submitted reports
            if f3x_data.get("dateSigned"):
                date_signed_array = f3x_data["dateSigned"].split("/")
                f3x_data["dateSignedMonth"] = date_signed_array[0]
                f3x_data["dateSignedDay"] = date_signed_array[1]
                f3x_data["dateSignedYear"] = date_signed_array[2]

            # build treasurer name to map it to PDF template
            treasurer_full_name = []
            treasurer_full_name.append(f3x_data.get("treasurerLastName"))
            treasurer_full_name.append(f3x_data.get("treasurerFirstName"))
            treasurer_full_name.append(f3x_data.get("treasurerMiddleName"))
            treasurer_full_name.append(f3x_data.get("treasurerPrefix"))
            treasurer_full_name.append(f3x_data.get("treasurerSuffix"))

            # removing empty string if any
            treasurer_full_name = list(filter(None, treasurer_full_name))

            f3x_data["treasurerFullName"] = ",".join(map(str, treasurer_full_name))
            f3x_data["treasurerName"] = (
                f3x_data["treasurerLastName"] + "," + f3x_data["treasurerFirstName"]
            )
            f3x_data["efStamp"] = "[Electronically Filed]"

            # checking if json contains summary details, for individual transactions print there wouldn't be summary
            if f3x_summary:
                total_no_of_pages = 5
                if silent_print or paginate:
                    txn_img_num = int(txn_img_num)
                    txn_img_num += 5
                f3x_data_summary_array = [f3x_data, f3x_summary]
                # if 'memoText' in f3x_data and f3x_data['memoText']:
                if f3x_data.get("memoText"):
                    total_no_of_pages += 1
                    if silent_print or paginate:
                        txn_img_num = int(txn_img_num)
                        txn_img_num += 1
            else:
                f3x_data_summary_array = [f3x_data]
            f3x_data_summary = {
                i: j for x in f3x_data_summary_array for i, j in x.items()
            }

            # process all schedules and build the PDF's if page_count AND paginate are False
            process_output, total_no_of_pages, txn_img_json = process_schedules_pages(
                f3x_data,
                md5_directory,
                total_no_of_pages,
                page_count,
                silent_print,
                paginate,
                txn_img_num,
            )

            # print("Total pages:", total_no_of_pages)

            for key, value in process_output.items():
                schedule_dict[key][0] = value

            if f3x_summary and not page_count and not paginate:
                f3x_data_summary["PAGESTR"] = (
                    "PAGE " + str(page_no) + " / " + str(total_no_of_pages)
                )

                if silent_print:
                    subtract_num = 6 if f3x_data.get("memoText") else 5
                    f3x_data_summary["IMGNO"] = txn_img_num - subtract_num
                    f3x_data_summary["IMGNO_FOR_PAGE2"] = txn_img_num - subtract_num + 1
                    f3x_data_summary["IMGNO_FOR_PAGE3"] = txn_img_num - subtract_num + 2
                    f3x_data_summary["IMGNO_FOR_PAGE4"] = txn_img_num - subtract_num + 3
                    f3x_data_summary["IMGNO_FOR_PAGE5"] = txn_img_num - subtract_num + 4

                    if filing_timestamp and page_no == 1:
                        f3x_data_summary["FILING_TIMESTAMP"] = filing_timestamp

                pypdftk.fill_form(infile, f3x_data_summary, outfile)
                shutil.copy(outfile, md5_directory + "F3X_Summary.pdf")
                os.remove(md5_directory + json_file_md5 + "_temp.pdf")

                # Memo text changes
                # if 'memoText' in f3x_data_summary and f3x_data_summary['memoText']:
                if f3x_data_summary.get("memoText"):
                    memo_dict = {}
                    temp_memo_outfile = md5_directory + "F3X_Summary_memo.pdf"
                    memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                        "TEXT"
                    )
                    memo_dict["scheduleName_1"] = (
                        "F3X" + f3x_data_summary["amendmentIndicator"]
                    )
                    memo_dict["memoDescription_1"] = f3x_data_summary["memoText"]

                    if silent_print:
                        memo_dict["IMGNO"] = txn_img_num - subtract_num + 5
                        txn_img_num += 1

                    memo_dict["PAGESTR"] = (
                        "PAGE " + str(6) + " / " + str(total_no_of_pages)
                    )
                    pypdftk.fill_form(memo_infile, memo_dict, temp_memo_outfile)
                    pypdftk.concat(
                        [md5_directory + "F3X_Summary.pdf", temp_memo_outfile],
                        md5_directory + json_file_md5 + "_temp.pdf",
                    )
                    shutil.copy(
                        md5_directory + json_file_md5 + "_temp.pdf",
                        md5_directory + "F3X_Summary.pdf",
                    )
                    os.remove(md5_directory + json_file_md5 + "_temp.pdf")

                # checking for transactions
                for key in schedule_key_list:
                    if key == "has_sa_schedules":
                        if schedule_dict[key][0]:
                            pypdftk.concat(
                                [
                                    md5_directory + "F3X_Summary.pdf",
                                    md5_directory
                                    + schedule_dict[key][1]
                                    + "/all_pages.pdf",
                                ],
                                md5_directory + "all_pages.pdf",
                            )
                            os.remove(
                                md5_directory + schedule_dict[key][1] + "/all_pages.pdf"
                            )
                            shutil.rmtree(md5_directory + schedule_dict[key][1])
                        else:
                            shutil.copy(
                                md5_directory + "F3X_Summary.pdf",
                                md5_directory + "all_pages.pdf",
                            )

                    elif key != "has_sa_schedules" and schedule_dict[key][0]:
                        pypdftk.concat(
                            [
                                md5_directory + "all_pages.pdf",
                                md5_directory
                                + schedule_dict[key][1]
                                + "/all_pages.pdf",
                            ],
                            md5_directory + "temp_all_pages.pdf",
                        )
                        shutil.move(
                            md5_directory + "temp_all_pages.pdf",
                            md5_directory + "all_pages.pdf",
                        )
                        os.remove(
                            md5_directory + schedule_dict[key][1] + "/all_pages.pdf"
                        )
                        shutil.rmtree(md5_directory + schedule_dict[key][1])

            elif not page_count and not paginate:
                # no summary, expecting it to be from individual transactions
                for key in schedule_key_list:
                    if key == "has_sa_schedules" and schedule_dict[key][0]:
                        shutil.move(
                            md5_directory + schedule_dict[key][1] + "/all_pages.pdf",
                            # md5_directory + schedule_dict[key][1] + "SA/all_pages.pdf",
                            md5_directory + "all_pages.pdf",
                        )
                        shutil.rmtree(md5_directory + schedule_dict[key][1])

                    elif key != "has_sa_schedules" and schedule_dict[key][0]:
                        if path.exists(md5_directory + "all_pages.pdf"):
                            pypdftk.concat(
                                [
                                    md5_directory + "all_pages.pdf",
                                    md5_directory
                                    + schedule_dict[key][1]
                                    + "/all_pages.pdf",
                                ],
                                md5_directory + "temp_all_pages.pdf",
                            )
                            shutil.move(
                                md5_directory + "temp_all_pages.pdf",
                                md5_directory + "all_pages.pdf",
                            )
                        else:
                            shutil.move(
                                md5_directory
                                + schedule_dict[key][1]
                                + "/all_pages.pdf",
                                md5_directory + "all_pages.pdf",
                            )
                        shutil.rmtree(md5_directory + schedule_dict[key][1])

                        if key == "has_sc_schedules":
                            os.remove(
                                md5_directory + schedule_dict[key][1] + "/all_pages.pdf"
                            )
                        # elif key in ["has_sla_schedules", "has_slb_schedules"]:
                        # os.remove(md5_directory + schedule_dict[key][1] + '/all_pages.pdf')

            if not page_count and not paginate:
                # push output file to AWS
                s3 = boto3.client('s3')
                s3.upload_file(md5_directory + 'all_pages.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                 			md5_directory + 'all_pages.pdf',
                 			ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})

                response = {
                    # 'file_name': '{}.pdf'.format(json_file_md5),
                    "pdf_url": current_app.config["PRINT_OUTPUT_FILE_URL"].format(
                        json_file_md5
                    )
                    + "all_pages.pdf",
                    "total_pages": total_no_of_pages,
                }

            elif page_count and not paginate:
                response = {
                    "total_pages": total_no_of_pages,
                }
            elif not page_count and paginate:
                response = {
                    "total_pages": total_no_of_pages,
                    "txn_img_json": txn_img_json,
                }

            # return response
            if flask.request.method == "POST":
                envelope = common.get_return_envelope(data=response)
                status_code = (
                    status.HTTP_201_CREATED if not page_count else status.HTTP_200_OK
                )
                return flask.jsonify(**envelope), status_code

        else:
            error_type = "json_file"
            if paginate:
                error_type += "_name"
            if flask.request.method == "POST":
                envelope = common.get_return_envelope(
                    "false", error_type + " is missing from your request"
                )
                status_code = status.HTTP_400_BAD_REQUEST
                return flask.jsonify(**envelope), status_code
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        return error("Error generating print preview, error message: " + str(e))


# This method processes different schedules and calculates total_no_of_pages


def process_schedules_pages(
    f3x_data,
    md5_directory,
    total_no_of_pages,
    page_count=False,
    silent_print=False,
    paginate=False,
    txn_img_num=None,
):
    # Calculate total number of pages for schedules
    sb_line_numbers = ["21B", "22", "23", "26", "27", "28A", "28B", "28C", "29", "30B"]
    sc_sa_line_numbers = ["13", "14"]
    sc_sb_line_numbers = ["26", "27"]
    se_line_numbers = ["24"]
    # sf_line_numbers=[]
    # slb_line_numbers = []

    sa_schedules, sb_schedules, sc_schedules = [], [], []
    sd_schedules, se_schedules, sf_schedules = [], [], []
    sh_schedules = []
    sl_summary, sla_schedules, slb_schedules, = (
        [],
        [],
        [],
    )

    total_sc_pages = total_sd_pages = 0
    totalOutstandingLoans = 0

    if paginate:
        txn_img_num = txn_img_num - 1
        txn_img_json = {}

    try:
        # check if schedules exist in data file
        if "schedules" in f3x_data:
            schedules = f3x_data["schedules"]

            # Checking SC first as it has SA and SB transactions in it
            if schedules.get("SC"):
                sc_schedules = schedules["SC"]
                sc1_schedules = []
                sc1_schedules_cnt = additional_sc_pg_cnt = 0
                sc_memo_page_cnt = sc1_memo_page_cnt = 0

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SC", exist_ok=True)

                for schedule in sc_schedules:
                    if schedule.get("memoDescription"):
                        sc_memo_page_cnt += 1

                    if schedule.get("child"):
                        sc_child_schedules = schedule["child"]
                        sc2_schedules_cnt = 0

                        for child_schedule in sc_child_schedules:
                            if child_schedule.get("lineNumber") in sc_sa_line_numbers:
                                if not schedules.get("SA"):
                                    schedules["SA"] = []
                                schedules["SA"].append(child_schedule)
                            elif child_schedule.get("lineNumber") in sc_sb_line_numbers:
                                if not schedules.get("SA"):
                                    schedules["SB"] = []
                                schedules["SB"].append(child_schedule)
                            elif child_schedule["transactionTypeIdentifier"] in ["SC1"]:
                                sc1_schedules.append(child_schedule)
                                sc1_schedules_cnt += 1
                                if child_schedule.get("memoDescription"):
                                    sc1_memo_page_cnt += 1
                            elif child_schedule["transactionTypeIdentifier"] in ["SC2"]:
                                sc2_schedules_cnt += 1

                        if sc2_schedules_cnt > 4:
                            additional_sc_pg_cnt += int(sc2_schedules_cnt // 4)

                total_sc_pages = (
                    len(sc_schedules)
                    + sc1_schedules_cnt
                    + sc1_memo_page_cnt
                    + sc_memo_page_cnt
                    + additional_sc_pg_cnt
                )
            # print("total_sc_pages", total_sc_pages)

            # Checking SD before SB as SD has SB transactions as childs
            if schedules.get("SD"):
                sd_schedules = schedules["SD"]

                line_9_list = []
                line_10_list = []

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SD", exist_ok=True)

                for schedule in sd_schedules:
                    if schedule.get("lineNumber") == "9":
                        line_9_list.append(schedule)
                    else:
                        line_10_list.append(schedule)

                    if schedule.get("child"):
                        child_schedules = schedule["child"]
                        for child_schedule in child_schedules:
                            if child_schedule.get("transactionTypeIdentifier") in [
                                "OPEXP_DEBT",
                                "FEA_100PCT_DEBT_PAY",
                                "OTH_DISB_DEBT",
                            ]:
                                if not schedules.get("SB"):
                                    schedules["SB"] = []
                                schedules["SB"].append(child_schedule)

                if line_9_list:
                    total_sd_pages += int(len(line_9_list) // 4) + 1

                if line_10_list:
                    total_sd_pages += int(len(line_10_list) // 4) + 1

                sd_dict = {"9": line_9_list, "10": line_10_list}
            # print("total_sd_pages", total_sd_pages)

            if schedules.get("SA"):
                sa_start_page = total_no_of_pages
                sa_schedules.extend(schedules["SA"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SA", exist_ok=True)

                # building object for all SA line numbers
                sa_line_numbers_dict = OrderedDict()

                sa_line_numbers_dict["11A1"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["11B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["11C"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["12"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["13"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["14"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["15"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["16"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sa_line_numbers_dict["17"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }

                # process for each Schedule A
                for schedule in sa_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]

                        for child_schedule in child_schedules:
                            if child_schedule["lineNumber"] in sb_line_numbers:
                                sb_schedules.append(child_schedule)
                            else:
                                sa_schedules.append(child_schedule)

                for schedule in sa_schedules:
                    process_sa_line_numbers(sa_line_numbers_dict, schedule)

                # calculate number of pages for each SA line numbers and add to total_no_of_pages
                for key, value in sa_line_numbers_dict.items():
                    value["page_cnt"], value["memo_page_cnt"] = calculate_page_count(
                        schedules=value["data"], num=3
                    )
                    total_no_of_pages += value["page_cnt"] + value["memo_page_cnt"]

                    if paginate:
                        map_txn_img_num(
                            schedules=value["data"],
                            num=3,
                            txn_img_json=txn_img_json,
                            image_num=txn_img_num,
                        )
                        txn_img_num += value["page_cnt"] + value["memo_page_cnt"]

                sb_start_page = total_no_of_pages
            # print("sa total page count:", total_no_of_pages)

            if schedules.get("SB"):
                sb_start_page = total_no_of_pages
                sb_schedules.extend(schedules["SB"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SB", exist_ok=True)

                # building object for all SB line numbers
                sb_line_numbers_dict = OrderedDict()
                sb_line_numbers_dict["21B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["22"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["23"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["26"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["27"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["28A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["28B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["28C"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["29"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sb_line_numbers_dict["30B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }

                # process for each Schedule B
                for schedule in sb_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]

                        for child_schedule in child_schedules:
                            if child_schedule["lineNumber"] in sb_line_numbers:
                                sb_schedules.append(child_schedule)

                for schedule in sb_schedules:
                    process_line_numbers(sb_line_numbers_dict, schedule)

                for key, value in sb_line_numbers_dict.items():
                    value["page_cnt"], value["memo_page_cnt"] = calculate_page_count(
                        schedules=value["data"], num=3
                    )
                    total_no_of_pages += value["page_cnt"] + value["memo_page_cnt"]

                    if paginate:
                        map_txn_img_num(
                            schedules=value["data"],
                            num=3,
                            txn_img_json=txn_img_json,
                            image_num=txn_img_num,
                        )
                        txn_img_num += value["page_cnt"] + value["memo_page_cnt"]

            # print("sb total_no_of_pages: ", total_no_of_pages)

            if total_sc_pages:
                sc_start_page = total_no_of_pages + 1
                total_no_of_pages += total_sc_pages

                if paginate and sc_schedules:
                    for data in sc_schedules:
                        if data.get("transactionId"):
                            txn_img_num += 1
                            txn_img_json[data["transactionId"]] = txn_img_num

                        if data.get("memoDescription"):
                            txn_img_num += 1

                if paginate and sc1_schedules:
                    for data in sc1_schedules:
                        if data["transactionTypeIdentifier"] in ["SC1"]:
                            txn_img_num += 1
                            txn_img_json[data["transactionId"]] = txn_img_num

                        if data.get("memoDescription"):
                            txn_img_num += 1

            # print("sc total_no_of_pages: ", total_no_of_pages)

            if total_sd_pages:
                sd_start_page = total_no_of_pages + 1
                total_no_of_pages += total_sd_pages

                if paginate and line_9_list:
                    count = 0
                    for data in line_9_list:
                        count += 1
                        if data.get("transactionId"):
                            txn_img_json[data["transactionId"]] = txn_img_num + 1

                        if count == 3:
                            txn_img_num += 1
                            count = 0

                    if count:
                        txn_img_num += 1

                if paginate and line_10_list:
                    count = 0
                    for data in line_10_list:
                        count += 1
                        if data.get("transactionId"):
                            txn_img_json[data["transactionId"]] = txn_img_num + 1

                        if count == 3:
                            txn_img_num += 1
                            count = 0

                    if count:
                        txn_img_num += 1

            # print("sd total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SE"):
                se_start_page = total_no_of_pages
                se_schedules.extend(schedules["SE"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SE", exist_ok=True)

                se_line_numbers_dict = OrderedDict()
                se_line_numbers_dict["24"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }

                for schedule in se_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]

                        for child_schedule in child_schedules:
                            if child_schedule["lineNumber"] in se_line_numbers:
                                se_schedules.append(child_schedule)

                for schedule in se_schedules:
                    process_line_numbers(se_line_numbers_dict, schedule)

                for key, value in se_line_numbers_dict.items():
                    value["page_cnt"], value["memo_page_cnt"] = calculate_page_count(
                        schedules=value["data"], num=2
                    )
                    total_no_of_pages += value["page_cnt"] + value["memo_page_cnt"]

                if paginate:
                    map_txn_img_num(
                        schedules=value["data"],
                        num=2,
                        txn_img_json=txn_img_json,
                        image_num=txn_img_num,
                    )
                    txn_img_num += value["page_cnt"] + value["memo_page_cnt"]

            # print("se total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SF"):
                sf_start_page = total_no_of_pages
                sf_schedules.extend(schedules.get("SF"))

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SF", exist_ok=True)

                sf_crd = []
                sf_non_crd = []
                sf_empty_ord = []
                sf_empty_non_ord = []
                sf_empty_none = []
                sf_empty_sub = []
                sf_crd_memo = []
                sf_non_crd_memo = []
                sf_empty_ord_memo = []
                sf_empty_non_ord_memo = []
                sf_empty_none_memo = []
                sf_empty_sub_memo = []

                sf_crd_page_cnt = sf_crd_memo_page_cnt = 0

                # sf_non_crd_page_cnt = sf_empty_ord_page_cnt = sf_empty_non_ord_page_cnt = 0
                # sf_empty_none_page_cnt = sf_non_sub_page_cnt = 0

                # sf_non_crd_memo_page_cnt = sf_empty_ord_memo_page_cnt = sf_empty_non_ord_memo_page_cnt = 0
                # sf_empty_none_memo_page_cnt = sf_non_sub_memo_page_cnt = 0

                for schedule in sf_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]
                        for child_schedule in child_schedules:
                            sf_schedules.append(child_schedule)

                for schedule in sf_schedules:
                    process_sf_line_numbers(
                        sf_crd,
                        sf_non_crd,
                        sf_empty_ord,
                        sf_empty_non_ord,
                        sf_empty_none,
                        sf_empty_sub,
                        sf_crd_memo,
                        sf_non_crd_memo,
                        sf_empty_ord_memo,
                        sf_empty_non_ord_memo,
                        sf_empty_none_memo,
                        sf_empty_sub_memo,
                        schedule,
                    )

                cor_exp = list(set([sub["designatingCommitteeName"] for sub in sf_crd]))
                non_cor_exp = list(
                    set([sub["subordinateCommitteeName"] for sub in sf_non_crd])
                )
                empty_non_ord = list(
                    set([sub["subordinateCommitteeName"] for sub in sf_empty_non_ord])
                )
                empty_ord = list(
                    set([sub["designatingCommitteeName"] for sub in sf_empty_ord])
                )
                sf_none = list(set([sub["lineNumber"] for sub in sf_empty_none]))
                sf_sub_none = list(set([sub["lineNumber"] for sub in sf_empty_sub]))

                newdict_cor = {}
                for val in range(len(cor_exp)):
                    for i in sf_crd:
                        if (
                            i["coordinateExpenditure"] == "Y"
                            and i["designatingCommitteeName"] == cor_exp[val]
                        ):
                            if cor_exp[val] not in newdict_cor:
                                newdict_cor[cor_exp[val]] = [i]
                            else:
                                newdict_cor[cor_exp[val]].append(i)

                newdict_non_cor = {}
                for val in range(len(non_cor_exp)):
                    for i in sf_non_crd:
                        if (
                            i["coordinateExpenditure"] == "N"
                            and i["subordinateCommitteeName"] == non_cor_exp[val]
                        ):
                            if non_cor_exp[val] not in newdict_non_cor:
                                newdict_non_cor[non_cor_exp[val]] = [i]
                            else:
                                newdict_non_cor[non_cor_exp[val]].append(i)

                newdict_empty_ord = {}
                if len(newdict_empty_ord) >= 0:
                    for val in range(len(empty_ord)):
                        for i in sf_empty_ord:
                            if (
                                i["coordinateExpenditure"] == ""
                                and i["subordinateCommitteeName"] == ""
                            ):
                                if empty_ord[val] not in newdict_empty_ord:
                                    newdict_empty_ord[empty_ord[val]] = [i]
                                else:
                                    newdict_empty_ord[empty_ord[val]].append(i)

                newdict_empty_non_ord = {}
                if len(empty_non_ord) >= 0:
                    for val in range(len(empty_non_ord)):
                        for i in sf_empty_non_ord:
                            if (
                                i["coordinateExpenditure"] == ""
                                and i["designatingCommitteeName"] == ""
                            ):
                                if empty_non_ord[val] not in newdict_empty_non_ord:
                                    newdict_empty_non_ord[empty_non_ord[val]] = [i]
                                else:
                                    newdict_empty_non_ord[empty_non_ord[val]].append(i)

                newdict_sf_none = {}
                if len(newdict_sf_none) >= 0:
                    for val in range(len(sf_none)):
                        for i in sf_empty_none:
                            if (
                                i["coordinateExpenditure"] == ""
                                and i["subordinateCommitteeName"] == ""
                                and i["designatingCommitteeName"] == ""
                            ):
                                if sf_none[val] not in newdict_sf_none:
                                    newdict_sf_none[sf_none[val]] = [i]
                                else:
                                    newdict_sf_none[sf_none[val]].append(i)

                newdict_sf_sub_none = {}
                for val in range(len(sf_sub_none)):
                    for i in sf_empty_sub:
                        if (
                            i["coordinateExpenditure"] == "N"
                            and i["subordinateCommitteeName"] == ""
                        ):
                            if sf_sub_none[val] not in newdict_sf_sub_none:
                                newdict_sf_sub_none[sf_sub_none[val]] = [i]
                            else:
                                newdict_sf_sub_none[sf_sub_none[val]].append(i)

                list_dirs = [
                    newdict_cor,
                    newdict_non_cor,
                    newdict_empty_non_ord,
                    newdict_empty_ord,
                    newdict_sf_none,
                    newdict_sf_sub_none,
                ]

                for lis in list_dirs:
                    if lis == newdict_cor:
                        values = list(newdict_cor.values())

                    if lis == newdict_non_cor:
                        values = list(newdict_non_cor.values())

                    if lis == newdict_empty_non_ord:
                        values = list(newdict_empty_non_ord.values())

                    if lis == newdict_empty_ord:
                        values = list(newdict_empty_ord.values())

                    if lis == newdict_sf_none:
                        values = list(newdict_sf_none.values())

                    if lis == newdict_sf_sub_none:
                        values = list(newdict_sf_sub_none.values())

                    for val in values:
                        sf_crd_page_cnt, sf_crd_memo_page_cnt = calculate_page_count(
                            schedules=val, num=3
                        )
                        total_no_of_pages += sf_crd_page_cnt + sf_crd_memo_page_cnt

                        if paginate:
                            map_txn_img_num(
                                schedules=val,
                                num=3,
                                txn_img_json=txn_img_json,
                                image_num=txn_img_num,
                            )
                            txn_img_num += sf_crd_page_cnt + sf_crd_memo_page_cnt

            # print("sf total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SH"):
                # sh_start_page = total_no_of_pages
                sh_schedules.extend(schedules.get("SH"))

                # building object for all SA line numbers
                sh_line_numbers_dict = OrderedDict()

                # No memo for H1 & H2 & 18A (H3)
                sh_line_numbers_dict["H1"] = {
                    "data": [],
                    "page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh1_line,
                }
                sh_line_numbers_dict["H2"] = {
                    "data": [],
                    "page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh2_line,
                }
                sh_line_numbers_dict["18A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh3_line,
                }
                sh_line_numbers_dict["18B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh5_line,
                }
                sh_line_numbers_dict["21A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh4_line,
                }
                sh_line_numbers_dict["30A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                    "start_page": 0,
                    "methodName": print_sh6_line,
                }

                sh_line_numbers = ["18A", "18B", "21A", "30A"]

                for schedule in sh_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]

                        for child_schedule in child_schedules:
                            if child_schedule["lineNumber"] in sh_line_numbers:
                                sh_schedules.append(child_schedule)

                for schedule in sh_schedules:
                    process_sh_line_numbers(sh_line_numbers_dict, schedule)

                for key, value in sh_line_numbers_dict.items():
                    if value["data"]:
                        if key == "H1":
                            value["start_page"] = total_no_of_pages

                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH1", exist_ok=True)

                            value["page_cnt"] = 1
                            total_no_of_pages += len(value["data"])

                            if paginate:
                                txn_img_num += len(value["data"])
                            # print("H1", total_no_of_pages)

                        elif key == "H2":
                            value["start_page"] = total_no_of_pages
                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH2", exist_ok=True)
                            value["page_cnt"], _ = calculate_page_count(
                                schedules=value["data"], num=6
                            )
                            total_no_of_pages += value["page_cnt"]

                            if paginate:
                                map_txn_img_num(
                                    schedules=value["data"],
                                    num=6,
                                    txn_img_json=txn_img_json,
                                    image_num=txn_img_num,
                                )
                                txn_img_num += value["page_cnt"]
                            # print("H2", total_no_of_pages)

                        elif key == "18A":
                            value["start_page"] = total_no_of_pages
                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH3", exist_ok=True)

                            # using custom method for page count
                            value["page_cnt"] = calculate_sh3_page_count(
                                schedules=value["data"]
                            )
                            total_no_of_pages += value["page_cnt"]

                            if paginate:
                                map_txn_img_num(
                                    schedules=value["data"],
                                    num=1,
                                    txn_img_json=txn_img_json,
                                    image_num=txn_img_num,
                                )
                                txn_img_num += value["page_cnt"]

                            # print("18A", total_no_of_pages)

                        elif key == "18B":
                            value["start_page"] = total_no_of_pages
                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH5", exist_ok=True)
                            (
                                value["page_cnt"],
                                value["memo_page_cnt"],
                            ) = calculate_page_count(schedules=value["data"], num=2)
                            total_no_of_pages += (
                                value["page_cnt"] + value["memo_page_cnt"]
                            )

                            if paginate:
                                map_txn_img_num(
                                    schedules=value["data"],
                                    num=2,
                                    txn_img_json=txn_img_json,
                                    image_num=txn_img_num,
                                )
                                txn_img_num += (
                                    value["page_cnt"] + value["memo_page_cnt"]
                                )
                            # print("18B", total_no_of_pages)

                        elif key == "21A":
                            value["start_page"] = total_no_of_pages
                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH4", exist_ok=True)
                            (
                                value["page_cnt"],
                                value["memo_page_cnt"],
                            ) = calculate_page_count(schedules=value["data"], num=3)
                            total_no_of_pages += (
                                value["page_cnt"] + value["memo_page_cnt"]
                            )

                            if paginate:
                                map_txn_img_num(
                                    schedules=value["data"],
                                    num=3,
                                    txn_img_json=txn_img_json,
                                    image_num=txn_img_num,
                                )
                                txn_img_num += (
                                    value["page_cnt"] + value["memo_page_cnt"]
                                )
                            # print("21A", total_no_of_pages)

                        elif key == "30A":
                            value["start_page"] = total_no_of_pages

                            if not page_count and not paginate:
                                os.makedirs(md5_directory + "SH6", exist_ok=True)

                            (
                                value["page_cnt"],
                                value["memo_page_cnt"],
                            ) = calculate_page_count(schedules=value["data"], num=3)
                            total_no_of_pages += (
                                value["page_cnt"] + value["memo_page_cnt"]
                            )

                            if paginate:
                                map_txn_img_num(
                                    schedules=value["data"],
                                    num=3,
                                    txn_img_json=txn_img_json,
                                    image_num=txn_img_num,
                                )
                                txn_img_num += (
                                    value["page_cnt"] + value["memo_page_cnt"]
                                )
                            # print("30A", total_no_of_pages)

            # print("sh total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SL"):
                sl_start_page = total_no_of_pages
                # total_no_of_pages += len(sl_summary)
                sl_summary.extend(schedules["SL"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SL", exist_ok=True)

                levin_name_data = OrderedDict()

                for schedule in sl_summary:
                    levin_name = schedule["accountName"]
                    if not levin_name_data.get(levin_name):
                        levin_name_data[levin_name] = []
                        levin_name_data[levin_name].append(schedule)
                    else:
                        levin_name_data[levin_name].append(schedule)

                if levin_name_data:
                    for name, account_data in levin_name_data.items():
                        total_no_of_pages += len(account_data)

                        if paginate:
                            for data in account_data:
                                if data.get("transactionId"):
                                    txn_img_num += 1
                                    txn_img_json[data["transactionId"]] = txn_img_num
            # print("sl total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SL-A"):
                sla_start_page = total_no_of_pages
                sla_schedules.extend(schedules["SL-A"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SL-A", exist_ok=True)

                sla_line_numbers_dict = OrderedDict()
                sla_line_numbers_dict["1A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                sla_line_numbers_dict["2"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }

                for schedule in sla_schedules:
                    if schedule.get("child"):
                        child_schedules = schedule["child"]
                        for child_schedule in child_schedules:
                            sla_schedules.append(child_schedule)

                for schedule in sla_schedules:
                    process_line_numbers(sla_line_numbers_dict, schedule)

                for key, value in sla_line_numbers_dict.items():
                    value["page_cnt"], value["memo_page_cnt"] = calculate_page_count(
                        schedules=value["data"], num=4
                    )
                    total_no_of_pages += value["page_cnt"] + value["memo_page_cnt"]

                    if paginate:
                        map_txn_img_num(
                            schedules=value["data"],
                            num=4,
                            txn_img_json=txn_img_json,
                            image_num=txn_img_num,
                        )
                        txn_img_num += value["page_cnt"] + value["memo_page_cnt"]

                slb_start_page = total_no_of_pages
            # print("sl-a total_no_of_pages: ", total_no_of_pages)

            if schedules.get("SL-B"):
                slb_start_page = total_no_of_pages
                slb_schedules.extend(schedules["SL-B"])

                if not page_count and not paginate:
                    os.makedirs(md5_directory + "SL-B", exist_ok=True)

                slb_line_numbers_dict = OrderedDict()
                slb_line_numbers_dict["4A"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                slb_line_numbers_dict["4B"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                slb_line_numbers_dict["4C"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                slb_line_numbers_dict["4D"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }
                slb_line_numbers_dict["5"] = {
                    "data": [],
                    "page_cnt": 0,
                    "memo_page_cnt": 0,
                }

                for schedule in slb_schedules:
                    process_line_numbers(slb_line_numbers_dict, schedule)

                for key, value in slb_line_numbers_dict.items():
                    value["page_cnt"], value["memo_page_cnt"] = calculate_page_count(
                        schedules=value["data"], num=5
                    )
                    total_no_of_pages += value["page_cnt"] + value["memo_page_cnt"]

                if paginate:
                    map_txn_img_num(
                        schedules=value["data"],
                        num=5,
                        txn_img_json=txn_img_json,
                        image_num=txn_img_num,
                    )
                    txn_img_num += value["page_cnt"] + value["memo_page_cnt"]
            # print("sl-b total_no_of_pages: ", total_no_of_pages)

        # to print image_numbers on pages if silent_print is True
        image_num = None
        if silent_print:
            image_num = txn_img_num

        # if page_count is True or paginate is True, then don't need to print pdf
        if not page_count and not paginate:
            # Printing schedules
            if sa_schedules:
                current_page_num = sa_start_page
                for key, value in sa_line_numbers_dict.items():
                    if value["data"]:
                        current_page_num, image_num = print_sa_line(
                            f3x_data,
                            md5_directory,
                            key,
                            value["data"],
                            value["page_cnt"],
                            current_page_num,
                            total_no_of_pages,
                            image_num,
                        )

            if sb_schedules:
                current_page_num = sb_start_page
                for key, value in sb_line_numbers_dict.items():
                    if value["data"]:
                        current_page_num, image_num = print_sb_line(
                            f3x_data,
                            md5_directory,
                            key,
                            value["data"],
                            value["page_cnt"],
                            current_page_num,
                            total_no_of_pages,
                            image_num,
                        )

            if sc_schedules:
                (
                    sc1_list,
                    sc1_start_page,
                    totalOutstandingLoans,
                    image_num,
                ) = print_sc_line(
                    f3x_data,
                    md5_directory,
                    sc_schedules,
                    sc_start_page,
                    total_no_of_pages,
                    image_num,
                )
                # else:
                # 	sc1_list = []

                if sc1_list:
                    for sc1 in sc1_list:
                        image_num = print_sc1_line(
                            f3x_data,
                            md5_directory,
                            sc1,
                            sc1_start_page,
                            total_no_of_pages,
                            image_num,
                        )
                        sc1_start_page += 1

            if sd_schedules:
                sd_total_balance, image_num = print_sd_line(
                    f3x_data,
                    md5_directory,
                    sd_dict,
                    sd_start_page,
                    total_no_of_pages,
                    total_sd_pages,
                    totalOutstandingLoans,
                    image_num,
                )

            if se_schedules:
                se_24_start_page = se_start_page
                for key, value in se_line_numbers_dict.items():
                    if value["data"]:
                        current_page_num, image_num = print_se_line(
                            f3x_data,
                            md5_directory,
                            key,
                            value["data"],
                            value["page_cnt"],
                            se_24_start_page,
                            total_no_of_pages,
                            image_num,
                        )

            if sf_schedules:
                count = 0
                # sf_memo = []
                for lis in list_dirs:
                    if lis == newdict_cor:
                        values = list(newdict_cor.values())
                    if lis == newdict_non_cor:
                        values = list(newdict_non_cor.values())
                    if lis == newdict_empty_non_ord:
                        values = list(newdict_empty_non_ord.values())
                    if lis == newdict_empty_ord:
                        values = list(newdict_empty_ord.values())
                    if lis == newdict_sf_none:
                        values = list(newdict_sf_none.values())
                    if lis == newdict_sf_sub_none:
                        values = list(newdict_sf_sub_none.values())

                    for rec in values:
                        if (
                            rec[0].get("designatingCommitteeName")
                            and rec[0].get("coordinateExpenditure") is "Y"
                        ):
                            cord_name = "designatingCommittee"
                        elif (
                            rec[0].get("designatingCommitteeName")
                            and rec[0].get("coordinateExpenditure") == ""
                        ):
                            cord_name = "designatingNamewithoutEXP"
                        elif (
                            rec[0].get("subordinateCommitteeName")
                            and rec[0].get("coordinateExpenditure") is "N"
                        ):
                            cord_name = "subCommittee"
                        elif (
                            rec[0].get("subordinateCommitteeName")
                            and rec[0].get("coordinateExpenditure") == ""
                        ):
                            cord_name = "subordinateCommitteewithoutEXP"

                        elif (
                            rec[0].get("subordinateCommitteeName") == ""
                            and rec[0].get("coordinateExpenditure") is "N"
                        ):
                            cord_name = "withsubCommittee"

                        else:
                            cord_name = "payee"

                        sf_crd_page_cnt, sf_crd_memo_page_cnt = calculate_page_count(
                            schedules=rec, num=3
                        )
                        if count == 0:
                            count += 1
                            sf_crd_start_page = sf_start_page
                            image_num = print_sf_line(
                                f3x_data,
                                md5_directory,
                                "25",
                                rec,
                                sf_crd_page_cnt,
                                sf_crd_start_page,
                                total_no_of_pages,
                                cord_name,
                                image_num,
                            )
                        elif count == 1:
                            count += 1
                            sf_non_crd_start_page = (
                                sf_crd_start_page
                                + sf_crd_page_cnt
                                + sf_crd_memo_page_cnt
                            )
                            image_num = print_sf_line(
                                f3x_data,
                                md5_directory,
                                "25",
                                rec,
                                sf_crd_page_cnt,
                                sf_non_crd_start_page,
                                total_no_of_pages,
                                cord_name,
                                image_num,
                            )
                        else:
                            count += 1
                            sf_non_crd_start_page = (
                                sf_non_crd_start_page
                                + sf_crd_page_cnt
                                + sf_crd_memo_page_cnt
                            )
                            image_num = print_sf_line(
                                f3x_data,
                                md5_directory,
                                "25",
                                rec,
                                sf_crd_page_cnt,
                                sf_non_crd_start_page,
                                total_no_of_pages,
                                cord_name,
                                image_num,
                            )

            if sh_schedules:
                for key, value in sh_line_numbers_dict.items():
                    if value["data"]:
                        if key in ["H1", "H2"]:
                            tran_type_ident = value["data"][0][
                                "transactionTypeIdentifier"
                            ]
                            if tran_type_ident:
                                image_num = value["methodName"](
                                    f3x_data,
                                    md5_directory,
                                    tran_type_ident,
                                    value["data"],
                                    value["page_cnt"],
                                    value["start_page"],
                                    total_no_of_pages,
                                    image_num,
                                )

                        else:
                            image_num = value["methodName"](
                                f3x_data,
                                md5_directory,
                                key,
                                value["data"],
                                value["page_cnt"],
                                value["start_page"],
                                total_no_of_pages,
                                image_num,
                            )

            if sl_summary and levin_name_data:
                for name, account_data in levin_name_data.items():
                    sl_levin_page_cnt = len(account_data)
                    sl_last_page_cnt = 1

                image_num = print_sl_levin(
                    f3x_data,
                    md5_directory,
                    name,
                    account_data,
                    sl_levin_page_cnt,
                    sl_start_page,
                    sl_last_page_cnt,
                    total_no_of_pages,
                    image_num,
                )

            if sla_schedules:
                current_page_num = sla_start_page
                for key, value in sla_line_numbers_dict.items():
                    if value["data"]:
                        image_num = print_sla_line(
                            f3x_data,
                            md5_directory,
                            key,
                            value["data"],
                            value["page_cnt"],
                            current_page_num,
                            total_no_of_pages,
                            image_num,
                        )

                        current_page_num += value["page_cnt"] + value["memo_page_cnt"]
                        # image_num += value['page_cnt'] + value['memo_page_cnt']

            if slb_schedules:
                current_page_num = slb_start_page
                for key, value in slb_line_numbers_dict.items():
                    if value["data"]:
                        image_num = print_slb_line(
                            f3x_data,
                            md5_directory,
                            key,
                            value["data"],
                            value["page_cnt"],
                            current_page_num,
                            total_no_of_pages,
                            image_num,
                        )

                        current_page_num += value["page_cnt"] + value["memo_page_cnt"]
                        # image_num += value['page_cnt'] + value['memo_page_cnt']

        output_data = OrderedDict()
        output_data["has_sa_schedules"] = bool(sa_schedules)
        output_data["has_sb_schedules"] = bool(sb_schedules)
        output_data["has_sc_schedules"] = bool(sc_schedules)
        output_data["has_sd_schedules"] = bool(sd_schedules)
        output_data["has_se_schedules"] = bool(se_schedules)
        output_data["has_sf_schedules"] = bool(sf_schedules)
        output_data["has_sh1_schedules"] = bool(sh_schedules)
        output_data["has_sh2_schedules"] = bool(sh_schedules)
        output_data["has_sh3_schedules"] = bool(sh_schedules)
        output_data["has_sh4_schedules"] = bool(sh_schedules)
        output_data["has_sh5_schedules"] = bool(sh_schedules)
        output_data["has_sh6_schedules"] = bool(sh_schedules)
        output_data["has_sl_summary"] = bool(sl_summary)
        output_data["has_sla_schedules"] = bool(sla_schedules)
        output_data["has_slb_schedules"] = bool(slb_schedules)

        if sh_schedules:
            output_data["has_sh1_schedules"] = bool(sh_line_numbers_dict["H1"]["data"])
            output_data["has_sh2_schedules"] = bool(sh_line_numbers_dict["H2"]["data"])
            output_data["has_sh3_schedules"] = bool(sh_line_numbers_dict["18A"]["data"])
            output_data["has_sh4_schedules"] = bool(sh_line_numbers_dict["21A"]["data"])
            output_data["has_sh5_schedules"] = bool(sh_line_numbers_dict["18B"]["data"])
            output_data["has_sh6_schedules"] = bool(sh_line_numbers_dict["30A"]["data"])

        if paginate:
            return output_data, total_no_of_pages, txn_img_json
        return output_data, total_no_of_pages, None
    except:
        traceback.print_exception(*sys.exc_info())
