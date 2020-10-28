import flask
import boto3
import re
import os
import os.path
import pypdftk
import shutil
import urllib.request

from os import path
from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import common
from routes.src.utils import md5_for_text, md5_for_file, error


# stamp_print is a flag that will be passed at the time of submitting a report.
def print_pdftk(stamp_print):
    # check if json_file_name is in the request
    try:
        if "json_file" in request.files:
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
            image_num = None

            if silent_print:
                image_num = request.form.get("begin_image_num")

                if not image_num:
                    if flask.request.method == "POST":
                        envelope = common.get_return_envelope(
                            "false", "begin_image_num is missing from your request"
                        )
                        status_code = status.HTTP_400_BAD_REQUEST
                        return flask.jsonify(**envelope), status_code
                image_num = int(image_num)

                filing_timestamp = request.form.get("filing_timestamp")

            json_file_md5 = md5_for_file(json_file)
            json_file.stream.seek(0)

            # save json file as md5 file name
            json_file.save(
                current_app.config["REQUEST_FILE_LOCATION"].format(json_file_md5)
            )

            # load json file
            f1m_json = json.load(
                open(current_app.config["REQUEST_FILE_LOCATION"].format(json_file_md5))
            )

            # if page_count is True then return from here
            if page_count:
                response = {"total_pages": 1}

                if flask.request.method == "POST":
                    envelope = common.get_return_envelope(data=response)
                    status_code = status.HTTP_201_CREATED
                    return flask.jsonify(**envelope), status_code

            md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(
                json_file_md5
            )
            os.makedirs(md5_directory, exist_ok=True)
            infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("F1M")
            outfile = md5_directory + json_file_md5 + "_temp.pdf"

            # setting timestamp and imgno to empty as these needs to show up after submission
            if stamp_print != "stamp":
                f1m_json["FILING_TIMESTAMP"] = ""
                f1m_json["IMGNO"] = ""

            # read data from json file
            f1m_data = f1m_json["data"]

            # adding image_num if silent_print is True
            if silent_print:
                f1m_data["IMGNO"] = image_num
                if filing_timestamp:
                    f1m_data["FILING_TIMESTAMP"] = filing_timestamp

            name_list = ["LastName", "FirstName", "MiddleName", "Prefix", "Suffix"]

            # build treasurer name to map it to PDF template
            treasurerFullName = ""
            for item in name_list:
                item = "treasurer" + item
                if f1m_data.get(item):
                    treasurerFullName += f1m_data.get(item) + " "
            f1m_data["treasurerFullName"] = treasurerFullName[:-1]

            f1m_data["treasurerName"] = (
                f1m_data.get("treasurerLastName", "")
                + ", "
                + f1m_data.get("treasurerFirstName", "")
            )
            f1m_data["treasurerName"] = (
                f1m_data["treasurerName"].strip().rstrip(",").strip()
            )

            f1m_data["efStamp"] = "[Electronically Filed]"

            if "candidates" in f1m_data:
                for candidate in f1m_data["candidates"]:

                    candidateFullName = ""
                    for item in name_list:
                        item = "candidate" + item
                        if f1m_data.get(item):
                            candidateFullName += f1m_data.get(item) + " "
                    f1m_data[
                        "candidateName" + str(candidate["candidateNumber"])
                    ] = candidateFullName[:-1]

                    f1m_data[
                        "candidateOffice" + str(candidate["candidateNumber"])
                    ] = candidate["candidateOffice"]

                    f1m_data[
                        "candidateStateDist" + str(candidate["candidateNumber"])
                    ] = "/ ".join(
                        map(
                            str,
                            [
                                candidate["candidateState"],
                                candidate["candidateDistrict"],
                            ],
                        )
                    )

                    f1m_data[
                        "contributionDate" + str(candidate["candidateNumber"])
                    ] = candidate["contributionDate"]

            os.makedirs(md5_directory + str(f1m_data["reportId"]) + "/", exist_ok=True)
            infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("F1M")

            pypdftk.fill_form(infile, f1m_data, outfile)
            shutil.copy(outfile, md5_directory + str(f1m_data["reportId"]) + "/F1M.pdf")
            os.remove(outfile)

            # push output file to AWS
            s3 = boto3.client("s3")
            s3.upload_file(
                md5_directory + str(f1m_data["reportId"]) + "/F1M.pdf",
                current_app.config["AWS_FECFILE_COMPONENTS_BUCKET_NAME"],
                md5_directory + "F1M.pdf",
                ExtraArgs={"ContentType": "application/pdf", "ACL": "public-read"},
            )
            response = {
                # 'file_name': '{}.pdf'.format(json_file_md5),
                "pdf_url": current_app.config["PRINT_OUTPUT_FILE_URL"].format(
                    json_file_md5
                )
                + "F1M.pdf"
            }

            # return response
            if flask.request.method == "POST":
                envelope = common.get_return_envelope(data=response)
                status_code = status.HTTP_201_CREATED
                return flask.jsonify(**envelope), status_code

        else:
            if flask.request.method == "POST":
                envelope = common.get_return_envelope(
                    "false", "json_file_name is missing from your request"
                )
                status_code = status.HTTP_400_BAD_REQUEST
                return flask.jsonify(**envelope), status_code
    except Exception as e:
        return error("Error generating print preview, error message: " + str(e))


def paginate():
    if "json_file_name" in request.json:
        # json_file_name = request.json.get("json_file_name")

        begin_image_num = request.json.get("begin_image_num")
        if not begin_image_num:
            if flask.request.method == "POST":
                envelope = common.get_return_envelope(
                    "false", "begin_image_num is missing from your request"
                )
                status_code = status.HTTP_400_BAD_REQUEST
                return flask.jsonify(**envelope), status_code

        # file_url = current_app.config["AWS_S3_FECFILE_COMPONENTS_DOMAIN"] + "/" + json_file_name + ".json"
        # file_url = "https://dev-efile-repo.s3.amazonaws.com/" + json_file_name + ".json"

        # with urllib.request.urlopen(file_url) as url:
        #     file_content = url.read().decode()

        # f1m_json = json.loads(file_content)
        # data = f1m_json["data"]

        txn_img_json = {}
        total_no_of_pages = 1

        response = {"total_pages": total_no_of_pages, "txn_img_json": txn_img_json}

        if flask.request.method == "POST":
            envelope = common.get_return_envelope(data=response)
            status_code = status.HTTP_201_CREATED
            return flask.jsonify(**envelope), status_code
    else:
        if flask.request.method == "POST":
            envelope = common.get_return_envelope(
                "false", "json_file_name is missing from your request"
            )
            status_code = status.HTTP_400_BAD_REQUEST
            return flask.jsonify(**envelope), status_code
