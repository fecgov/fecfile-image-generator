import flask
import boto3
import os
import os.path
import pypdftk
import shutil

from os import path
from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import common
from routes.src.utils import md5_for_text, md5_for_file, error, delete_directory
from routes.src.f3x.helper import calculate_page_count, map_txn_img_num

name_list = ["LastName", "FirstName", "MiddleName", "Prefix", "Suffix"]


# stamp_print is a flag that will be passed at the time of submitting a report.
def print_pdftk(
    stamp_print="",
    page_count=False,
    file_content=None,
    begin_image_num=None,
    silent_print=False,
    filing_timestamp=None,
    rep_id=None,
):
    # try:
    silent_print = silent_print
    txn_img_num = begin_image_num
    filing_timestamp = filing_timestamp

    if "json_file" in request.files or (page_count and file_content):
        # check if json_file_name is in the request
        if "json_file" in request.files:
            json_file = request.files.get("json_file")
            page_count = page_count
            silent_print = (
                True
                if request.form.get("silent_print")
                and request.form.get("silent_print").lower() in ["true", "1"]
                else False
            )
            page_count = (
                True
                if request.form.get("page_count")
                and request.form.get("page_count").lower() in ["true", "1"]
                else False
            )

            if silent_print:
                txn_img_num = request.form.get("begin_image_num", None)

                if not txn_img_num:
                    if flask.request.method == "POST":
                        envelope = common.get_return_envelope(
                            "false", "begin_image_num is missing from your request"
                        )
                        status_code = status.HTTP_400_BAD_REQUEST
                        return flask.jsonify(**envelope), status_code
                txn_img_num = int(txn_img_num)

                filing_timestamp = request.form.get("filing_timestamp", None)

            json_file_md5 = md5_for_file(json_file)
            json_file.stream.seek(0)

            # save json file as md5 file name
            json_file.save(
                current_app.config["REQUEST_FILE_LOCATION"].format(json_file_md5)
            )

            # load json file
            f24_json = json.load(
                open(current_app.config["REQUEST_FILE_LOCATION"].format(json_file_md5))
            )

        # if page_count is True then return from here
        elif page_count and file_content:
            f24_json = json.loads(file_content)
            # return {"total_pages": get_total_pages(f24_json.get("data"))}

            response = {"total_pages": get_total_pages(f24_json.get("data"))}

            # if flask.request.method == "POST":
            envelope = common.get_return_envelope(data=response)
            return flask.jsonify(**envelope), status.HTTP_200_OK
        elif silent_print and begin_image_num and file_content:
            json_file_md5 = md5_for_text(file_content)
            f24_json = json.loads(file_content)

        md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(json_file_md5)

        # deleting directory if it exists and has any content
        delete_directory(md5_directory)

        os.makedirs(md5_directory, exist_ok=True)

        # setting timestamp and imgno to empty as these needs to show up after submission
        output = {}
        if stamp_print != "stamp":
            output["FILING_TIMESTAMP"] = ""
            output["IMGNO"] = ""

        # read data from json file
        f24_data = f24_json["data"]
        reportId = str(f24_data["reportId"])

        os.makedirs(md5_directory + reportId + "/", exist_ok=True)

        output["committeeId"] = f24_data["committeeId"]
        output["committeeName"] = f24_data["committeeName"]
        output["reportType"] = f24_data["reportType"]
        output["amendIndicator"] = f24_data["amendIndicator"]

        output["efStamp"] = "[Electronically Filed]"
        if output["amendIndicator"] == "A":
            if f24_data["amendDate"]:
                amend_date_array = f24_data["amendDate"].split("/")
                output["amendDate_MM"] = amend_date_array[0]
                output["amendDate_DD"] = amend_date_array[1]
                output["amendDate_YY"] = amend_date_array[2]

        se_count = 0
        # Calculating total number of pages
        if not f24_data["schedules"].get("SE"):
            output["PAGENO"] = 1
            output["TOTALPAGES"] = 1
        else:
            se_count = len(f24_data["schedules"]["SE"])
            output["TOTALPAGES"] = get_total_pages(f24_data)

        # make it true when filing_timestamp has been passed for the first time
        is_file_timestamp = False

        # Printing report memo text page
        if f24_data.get("memoText") and f24_data.get("reportPrint"):
            memo_dict = {
                "scheduleName_1": "F3X" + f24_data["amendIndicator"],
                "memoDescription_1": f24_data["memoText"],
                "PAGESTR": "PAGE " + str(1) + " / " + str(output["TOTALPAGES"]),
            }

            if silent_print:
                memo_dict["IMGNO"] = txn_img_num
                txn_img_num += 1
                if filing_timestamp:
                    memo_dict["FILING_TIMESTAMP"] = filing_timestamp
                    is_file_timestamp = True

            print_summary(memo_dict, 1, reportId, json_file_md5)

        if f24_data.get("filedDate"):
            filed_date_array = f24_data["filedDate"].split("/")
            output["filedDate_MM"] = filed_date_array[0]
            output["filedDate_DD"] = filed_date_array[1]
            output["filedDate_YY"] = filed_date_array[2]

            # build treasurer name to map it to PDF template
            treasurerFullName = ""
            for item in name_list:
                item = "treasurer" + item
                if f24_data.get(item):
                    treasurerFullName += f24_data.get(item) + ", "
            output["treasurerFullName"] = treasurerFullName[:-2]

            output["treasurerName"] = (
                f24_data.get("treasurerLastName", "")
                + ", "
                + f24_data.get("treasurerFirstName", "")
            )
            output["treasurerName"] = (
                output["treasurerName"].strip().rstrip(",").strip()
            )

        if f24_data["schedules"].get("SE"):
            page_index = (
                2 if f24_data.get("memoText") and f24_data.get("reportPrint") else 1
            )
            page_dict = {}
            sub_total = 0
            total = 0
            for i, se in enumerate(f24_data["schedules"]["SE"]):
                index = (i % 2) + 1
                if se.get("payeeLastName"):
                    payeeName = ""
                    for item in name_list:
                        item = "payee" + item
                        if se.get(item):
                            payeeName += se.get(item) + ", "

                    page_dict["payeeName_" + str(index)] = payeeName[:-2]
                elif se.get("payeeOrganizationName"):
                    page_dict["payeeName_" + str(index)] = se["payeeOrganizationName"]

                page_dict["memoCode_" + str(index)] = se["memoCode"]
                page_dict["memoDescription_" + str(index)] = se["memoDescription"]
                page_dict["payeeStreet1_" + str(index)] = se["payeeStreet1"]
                page_dict["payeeStreet2_" + str(index)] = se["payeeStreet2"]
                page_dict["payeeCity_" + str(index)] = se["payeeCity"]
                page_dict["payeeState_" + str(index)] = se["payeeState"]
                page_dict["payeeZipCode_" + str(index)] = se["payeeZipCode"]
                page_dict["expenditureAmount_" + str(index)] = "{:.2f}".format(
                    se["expenditureAmount"]
                )
                page_dict["transactionId_" + str(index)] = se["transactionId"]
                page_dict["expenditurePurpose_" + str(index)] = se[
                    "expenditurePurposeDescription"
                ]
                page_dict["supportOppose_" + str(index)] = se["support/opposeCode"]
                page_dict["candidateOffice_" + str(index)] = se["candidateOffice"]
                page_dict["candidateState_" + str(index)] = se["candidateState"]
                page_dict["candidateDistrict_" + str(index)] = se["candidateDistrict"]
                page_dict["electionType_" + str(index)] = se["electionCode"][:1]
                page_dict["electionYear_" + str(index)] = se["electionCode"][1:]
                page_dict["electionOtherDescription_" + str(index)] = se[
                    "electionOtherDescription"
                ]
                page_dict["calendarYTD_" + str(index)] = "{:.2f}".format(
                    se["calendarYTDPerElectionForOffice"]
                )

                if se.get("disseminationDate"):
                    dissem_date_array = se["disseminationDate"].split("/")
                    page_dict["disseminationDate_MM_" + str(index)] = dissem_date_array[
                        0
                    ]
                    page_dict["disseminationDate_DD_" + str(index)] = dissem_date_array[
                        1
                    ]
                    page_dict["disseminationDate_YY_" + str(index)] = dissem_date_array[
                        2
                    ]

                if se.get("disbursementDate"):
                    disburse_date_array = se["disbursementDate"].split("/")
                    page_dict[
                        "disbursementDate_MM_" + str(index)
                    ] = disburse_date_array[0]
                    page_dict[
                        "disbursementDate_DD_" + str(index)
                    ] = disburse_date_array[1]
                    page_dict[
                        "disbursementDate_YY_" + str(index)
                    ] = disburse_date_array[2]

                candidateName = ""
                for item in name_list:
                    item = "candidate" + item
                    if se.get(item):
                        candidateName += se.get(item) + ", "

                if candidateName:
                    page_dict["candidateName_" + str(index)] = candidateName[:-2]
                else:
                    page_dict["candidateName_" + str(index)] = ""

                # 	if se[item]: candidate_name_list.append(se[item])
                # page_dict["candidateName_" + str(index)] = " ".join(candidate_name_list)

                if se.get("memoCode") != "X":
                    sub_total += se["expenditureAmount"]
                    total += se["expenditureAmount"]

                # print and reset
                if index % 2 == 0 or i == se_count - 1:
                    page_dict["PAGENO"] = page_index
                    page_dict["subTotal"] = "{:.2f}".format(sub_total)

                    if silent_print:
                        page_dict["IMGNO"] = txn_img_num
                        txn_img_num += 1
                        if filing_timestamp and not is_file_timestamp:
                            page_dict["FILING_TIMESTAMP"] = filing_timestamp
                            is_file_timestamp = True

                    if i == se_count - 1:
                        page_dict["total"] = "{:.2f}".format(total)

                    print_dict = {**output, **page_dict}
                    print_f24(print_dict, page_index, reportId, json_file_md5)
                    page_index += 1

                    memo_dict = {}
                    for xir in range(1, 3):
                        if page_dict.get("memoDescription_{}".format(xir)):
                            memo_dict["scheduleName_{}".format(xir)] = "SE"
                            memo_dict["memoDescription_{}".format(xir)] = page_dict[
                                "memoDescription_{}".format(xir)
                            ]
                            memo_dict["transactionId_{}".format(xir)] = page_dict[
                                "transactionId_{}".format(xir)
                            ]
                            memo_dict["PAGESTR"] = (
                                "PAGE "
                                + str(page_index)
                                + " / "
                                + str(output["TOTALPAGES"])
                            )

                            if silent_print:
                                memo_dict["IMGNO"] = txn_img_num

                    if silent_print:
                        txn_img_num += 1

                    if memo_dict:
                        print_summary(memo_dict, page_index, reportId, json_file_md5)
                        page_index += 1
                    page_dict = {}
                    sub_total = 0
        else:
            output["subTotal"] = "0.00"
            output["total"] = "0.00"
            print_f24(output, 1, reportId, json_file_md5)

        # Concatenating all generated pages
        for i in range(1, output["TOTALPAGES"] + 1, 1):
            if path.isfile(md5_directory + reportId + "/F24_temp.pdf"):
                pypdftk.concat(
                    [
                        md5_directory + reportId + "/F24_temp.pdf",
                        md5_directory + reportId + "/F24_{}.pdf".format(i),
                    ],
                    md5_directory + reportId + "/concat_F24.pdf",
                )
                os.rename(
                    md5_directory + reportId + "/concat_F24.pdf",
                    md5_directory + reportId + "/F24_temp.pdf",
                )
                os.remove(md5_directory + reportId + "/F24_{}.pdf".format(i))
            else:
                os.rename(
                    md5_directory + reportId + "/F24_{}.pdf".format(i),
                    md5_directory + reportId + "/F24_temp.pdf",
                )
        os.rename(
            md5_directory + reportId + "/F24_temp.pdf",
            md5_directory + reportId + "/F24.pdf",
        )

        response = {
            "total_pages": output["TOTALPAGES"],
        }

        if not page_count:
            s3 = boto3.client("s3")
            extraArgs = {"ContentType": "application/pdf", "ACL": "public-read"}

            if silent_print:
                response["pdf_url"] = (
                    current_app.config["AWS_FECFILE_COMPONENTS_BUCKET_NAME"],
                    rep_id + ".pdf",
                )

                s3.upload_file(
                    md5_directory + reportId + "/F24.pdf",
                    current_app.config["AWS_FECFILE_COMPONENTS_BUCKET_NAME"],
                    rep_id + ".pdf",
                    ExtraArgs=extraArgs,
                )
            else:
                response["pdf_url"] = (
                    current_app.config["PRINT_OUTPUT_FILE_URL"].format(json_file_md5)
                    + "F24.pdf",
                )

                s3.upload_file(
                    md5_directory + reportId + "/F24.pdf",
                    current_app.config["AWS_FECFILE_COMPONENTS_BUCKET_NAME"],
                    md5_directory + "F24.pdf",
                    ExtraArgs=extraArgs,
                )

        # if flask.request.method == "POST":
        envelope = common.get_return_envelope(data=response)
        return flask.jsonify(**envelope), status.HTTP_201_CREATED
    else:
        if page_count or silent_print:
            envelope = common.get_return_envelope(False, "")
        elif flask.request.method == "POST":
            envelope = common.get_return_envelope(
                False, "json_file is missing from your request"
            )
        return flask.jsonify(**envelope), status.HTTP_400_BAD_REQUEST


# except Exception as e:
# 	return error('Error generating print preview, error message: ' + str(e))


def print_f24(print_dict, page_index, reportId, json_file_md5):
    try:
        md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(json_file_md5)
        infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("F24")
        outfile = md5_directory + json_file_md5 + "_temp.pdf"
        pypdftk.fill_form(infile, print_dict, outfile)
        shutil.copy(
            outfile, md5_directory + reportId + "/F24_{}.pdf".format(page_index)
        )
        os.remove(outfile)
    except Exception as e:
        return error("print_f24 error, error message: " + str(e))


def print_summary(print_dict, page_index, reportId, json_file_md5):
    try:
        md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(json_file_md5)
        infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("TEXT")
        outfile = md5_directory + json_file_md5 + "_temp.pdf"
        pypdftk.fill_form(infile, print_dict, outfile)
        shutil.copy(
            outfile, md5_directory + reportId + "/F24_{}.pdf".format(page_index)
        )
        os.remove(outfile)
    except Exception as e:
        return error("print_f24_summ error, error message: " + str(e))


def paginate(file_content=None, begin_image_num=None):
    if file_content and begin_image_num:
        txn_img_num = begin_image_num
        # if "json_file_name" in request.json:
        #     json_file_name = request.json.get("json_file_name")

        #     txn_img_num = request.json.get("begin_image_num")
        #     if not txn_img_num:
        #         if flask.request.method == "POST":
        #             envelope = common.get_return_envelope(
        #                 "false", "begin_image_num is missing from your request"
        #             )
        #             status_code = status.HTTP_400_BAD_REQUEST
        #             return flask.jsonify(**envelope), status_code

        #     # file_url = current_app.config["AWS_S3_FECFILE_COMPONENTS_DOMAIN"] + "/" + json_file_name + ".json"
        #     file_url = "https://dev-efile-repo.s3.amazonaws.com/" + json_file_name + ".json"

        #     with urllib.request.urlopen(file_url) as url:
        #         file_content = url.read().decode()

        f24_json = json.loads(file_content)
        data = f24_json["data"]

        txn_img_json = {}
        total_no_of_pages = 0

        if not data.get("memoText") or not data.get("reportPrint"):
            txn_img_num -= 1

        if data.get("schedules") and data["schedules"].get("SE"):
            map_txn_img_num(
                schedules=data["schedules"]["SE"],
                num=2,
                txn_img_json=txn_img_json,
                image_num=txn_img_num,
            )
            total_no_of_pages = get_total_pages(data)

            summary = {}
            if txn_img_json:
                summary["begin_image_num"] = min(txn_img_json.values())
                summary["end_image_num"] = max(txn_img_json.values())
            else:
                summary["begin_image_num"] = begin_image_num
                summary["end_image_num"] = txn_img_num

            summary["committeeId"] = data.get("committeeId", None)
            txn_img_json["summary"] = summary
        # return True, {"total_pages": total_no_of_pages, "txn_img_json": txn_img_json}
        response = {"total_pages": total_no_of_pages, "txn_img_json": txn_img_json}

        # if flask.request.method == "POST":
        envelope = common.get_return_envelope(data=response)
        return flask.jsonify(**envelope), status.HTTP_200_OK
    else:
        # return False, None
        # if flask.request.method == "POST":
        envelope = common.get_return_envelope(
            False, "json_file_name is missing from your request"
        )
        return flask.jsonify(**envelope), status.HTTP_400_BAD_REQUEST


def get_total_pages(data):
    total_pages = 0
    if data.get("schedules") and data["schedules"].get("SE"):
        page_cnt, memo_page_cnt = calculate_page_count(
            schedules=data["schedules"]["SE"], num=2
        )
        total_pages = page_cnt + memo_page_cnt

    if data.get("memoText") and data.get("reportPrint"):
        total_pages += 1

    return total_pages
