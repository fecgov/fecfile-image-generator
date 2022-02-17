import logging
import flask
import boto3
import config as cfg
import urllib.request
import json
import requests

from flask import request
from flask_cors import CORS
from routes.src import tmoflask, form99, form1m, form24, common
from routes.src.f3x import form3x
from flask_api import status

logger = logging.getLogger()

app = flask.Blueprint("controllers", __name__)
APP = tmoflask.TMOFlask(__name__, instance_relative_config=True)
CORS(app)


@app.route("/", methods=["GET"])
@app.route("/app-name", methods=["GET"])
def index():
    return "fecfile-image-generator"


@app.route("/print", methods=["POST"])
def print_pdf():
    """
    This function is being invoked from FECFile and Vendors
    HTTP request needs to have form_type, file, and attachment_file
    form_type : F99
    json_file: please refer to below sample JSON
    :return: return JSON response
    sample 1:
    {
    "message": "",
    "results": {
        "pdf_url": "https://fecfile-dev-components.s3.amazonaws.com/output/bd78435a70a70d656145dae89e0e22bb.pdf"
    },
    "success": "true"
    }

    sample 2:
    {
    "message": "",
    "results": {
        "total_pages": 35
    },
    "success": "true"
    }
    """
    form_type = request.form["form_type"]
    if form_type == "F99":
        return form99.print_f99_pdftk_html()
    elif form_type == "F3X":
        return form3x.print_pdftk()
    elif form_type == "F1M":
        return form1m.print_pdftk()
    elif form_type == "F24":
        return form24.print_pdftk()


# @app.route("/paginate", methods=["POST"])
# def paginate_pdf():
#     """
#     This function is being invoked from FECFile and Vendors
#     HTTP request needs to have form_type, json_file_name, and begin_image_num
#     form_type : F99
#     json_file: please refer to below sample JSON
#     begin_image_num: 1
#     :return: return JSON response
#     sample:
#     {
#     "message": "",
#     "results": {
#         "total_pages": 35,
#         "txn_img_json: {
#             "xxx0200804xxxxxxx": 1,
#             "xxx0200123xxxxxxx": 2,
#         }
#     },
#     success": "true"
#     }
#     """
#     form_type = request.json["form_type"]
#     if form_type == "F99":
#         return form99.print_f99_pdftk_html(paginate=True)
#     elif form_type == "F3X":
#         return form3x.print_pdftk(paginate=True)
#     elif form_type == "F1M":
#         return form1m.paginate()
#     elif form_type == "F24":
#         return form24.paginate()

# attachment_file_content is for only F99
def _paginate_pdf(
    form_type=None,
    file_content=None,
    begin_image_num=None,
    attachment_file_content=None,
):
    if form_type == "F99":
        response, status = form99.print_f99_pdftk_html(
            paginate=True,
            file_content=file_content,
            begin_image_num=begin_image_num,
            attachment_file_content=attachment_file_content,
        )
    elif form_type == "F3X":
        response, status = form3x.print_pdftk(
            paginate=True, file_content=file_content, begin_image_num=begin_image_num
        )
    elif form_type == "F1M":
        response, status = form1m.paginate(
            file_content=file_content, begin_image_num=begin_image_num
        )
    elif form_type == "F24":
        response, status = form24.paginate(
            file_content=file_content, begin_image_num=begin_image_num
        )

    response = response.json.get("results")
    if status != 400:
        return response.get("total_pages"), response.get("txn_img_json")
    return None, None


@app.route("/stamp_print", methods=["POST"])
def stamp_print_pdf():
    """
    This function is being invoked from FECFile and Vendors
    HTTP request needs to have form_type, file, and attachment_file
    form_type : F99
    json_file: please refer to below sample JSON
    :return: return JSON response
    sample:
    {
    "message": "",
    "results": {
        "pdf_url": "https://fecfile-dev-components.s3.amazonaws.com/output/bd78435a70a70d656145dae89e0e22bb.pdf"
    },
    "success": "true"
    }
    """
    form_type = request.form["form_type"]
    if form_type == "F99":
        return form99.print_f99_pdftk_html("stamp")


def page_count_pdf(form_type=None, file_content=None):
    if form_type == "F99":
        response, status = form99.print_f99_pdftk_html(
            page_count=True, file_content=file_content
        )
    elif form_type == "F3X":
        response, status = form3x.print_pdftk(
            page_count=True, file_content=file_content
        )
    elif form_type == "F1M":
        response, status = form1m.print_pdftk(
            page_count=True, file_content=file_content
        )
    elif form_type == "F24":
        response, status = form24.print_pdftk(
            page_count=True, file_content=file_content
        )

    response = response.json.get("results")
    return response.get("total_pages") if status != 400 else None


def _print_pdf(
    form_type=None,
    file_content=None,
    begin_image_num=None,
    silent_print=False,
    filing_timestamp=None,
    attachment_file_content=None,
    rep_id=None,
):
    if form_type == "F99":
        response, status = form99.print_f99_pdftk_html(
            paginate=False,
            file_content=file_content,
            begin_image_num=begin_image_num,
            attachment_file_content=attachment_file_content,
            silent_print=silent_print,
            filing_timestamp=filing_timestamp,
            rep_id=rep_id,
        )
    elif form_type == "F3X":
        response, status = form3x.print_pdftk(
            paginate=False,
            file_content=file_content,
            begin_image_num=begin_image_num,
            silent_print=silent_print,
            filing_timestamp=filing_timestamp,
            rep_id=rep_id,
        )
    elif form_type == "F1M":
        response, status = form1m.print_pdftk(
            file_content=file_content,
            begin_image_num=begin_image_num,
            silent_print=silent_print,
            filing_timestamp=filing_timestamp,
            rep_id=rep_id,
        )
    elif form_type == "F24":
        response, status = form24.print_pdftk(
            file_content=file_content,
            begin_image_num=begin_image_num,
            silent_print=silent_print,
            filing_timestamp=filing_timestamp,
            rep_id=rep_id,
        )

    return response, status


@app.route("parse_next_in_image_number_queue", methods=["GET"])
def parse_next_in_image_number_queue():
    """*****************************************************************************************************************
                                 Function to manually run from UI/postman
    *****************************************************************************************************************"""
    if request.method == "GET":
        res = parse_next_filing_from_image_number_queue()
        return res


def parse_next_filing_from_image_number_queue():
    """*****************************************************************************************************************
                             Function will get the next report to image from imaging queue and processes it
    ********************************************************************************************************************
        1. Imaging worker will call this function on a set interval, say every 15 seconds
        2. This Function will read the message from the SQS one at a time and sets the visibility to N number of minutes
           so that other workers will not see it.

        Sample Message
        message_attributes = {'submissionId': {'StringValue': submission_id, 'DataType': 'String'},
                              'committeeId': {'StringValue': committee_id, 'DataType': 'String'},
                              'fileName': {'StringValue': file_name, 'DataType': 'String'},
                              'receivedTime': {'StringValue': str(upload_time), 'DataType': 'String'},
                              'beginImageNumber': {'StringValue': begin_image_number, 'DataType': 'String'}
                              }
    *****************************************************************************************************************"""
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=cfg.IMAGE_NUMBER_SQS_QUEUE)
    try:
        # Getting One message at a time
        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
            VisibilityTimeout=cfg.MESSAGE_VISIBILITY_TIMEOUT,
        )
    except Exception as e:
        envelope = common.get_return_envelope(
            "false", "unable to read message from image number queue"
        )
        return flask.jsonify(**envelope), status.HTTP_400_BAD_REQUEST
    # messages = {}
    # next_imaging = []
    # next_imaging.append({"submissionId":"fab1d0fc-0089-4b47-8b80-0a1f3f970066","committeeId":"C00337733",
    #                      "fileName": "C00337733_fab1d0fc00894b478b800a1f3f970066.json","beginImageNumber":""})
    # image_number = image_number_data(next_imaging[0])
    # message.delete()
    # print(image_number)

    if len(messages) > 0:
        # Getting the first message
        for message in messages:
            receipt_handle = message.receipt_handle
            # process the messages
            msg_body = message.body
            next_imaging = []
            print(
                "***************************************************************************************************"
            )
            print("Getting Message from the SQS: " + str(msg_body))
            print(message.message_attributes)
            print(
                "***************************************************************************************************"
            )
            if message.message_attributes is not None:
                next_imaging.append(
                    {
                        "submissionId": message.message_attributes.get(
                            "submissionId"
                        ).get("StringValue"),
                        "committeeId": message.message_attributes.get(
                            "committeeId"
                        ).get("StringValue"),
                        "fileName": message.message_attributes.get("fileName").get(
                            "StringValue"
                        ),
                        "beginImageNumber": message.message_attributes.get(
                            "beginImageNumber"
                        ).get("StringValue"),
                    }
                )
                # Parsing the data
                image_number = image_number_data(next_imaging[0])
                message.delete()
                print(image_number)
                # return res
                res = flask.jsonify({"result": [{"beginImageNum": str(image_number)}]})
                return res

    else:
        print("Nothing to process - Message Queue is empty")
        envelope = common.get_return_envelope(
            "true", "Nothing to process - Message Queue is empty"
        )
        # next_imaging = []
        # next_imaging.append(
        #     {
        #         "submissionId": "374d7ea3-1718-4763-b9f3-fee88acecc3c",
        #         "committeeId": "C00024679",
        #         "fileName": "C00024679_374d7ea317184763b9f3fee88acecc3c.json",
        #         "beginImageNumber": "20201109000000"
        #     }
        # )
        # image_number_data(next_imaging)

        return flask.jsonify(**envelope), status.HTTP_200_OK


def image_number_data(next_imaging=None):
    print(next_imaging)
    submission_id = next_imaging["submissionId"]
    committee_id = next_imaging["committeeId"]
    json_file_name = next_imaging["fileName"]
    begin_image_number = next_imaging["beginImageNumber"]
    # image number should not be null, temporarily assigning summy image number
    if begin_image_number != "":
        begin_image_number = "20201109000000"

    file_url = (
        "https://" + cfg.AWS_S3_PAGINATION_COMPONENTS_DOMAIN + "/" + json_file_name
    )
    # file_url = "https://dev-efile-repo.s3.amazonaws.com/" + file_name
    print(file_url)

    file_content = None
    json_data = None
    try:
        with urllib.request.urlopen(file_url) as url:
            file_content = url.read().decode()
        json_data = json.loads(file_content)
    except Exception as e:
        print(e)

    if json_data.get("data"):
        data = json_data.get("data")
        total_pages = page_count_pdf(data.get("formType"), file_content)
        # call parser to update begin image number
        data_obj = {
            "imageType": "EFILING",
            "candCmteId": committee_id,
            "formType": data.get("formType"),
            "reportType": data.get("reportCode"),
            "cvgStartDate": data.get("coverageStartDate"),
            "cvgEndDate": data.get("coverageEndDate"),
            "submissionId": submission_id,
            "totalPages": total_pages,
        }
        ## data_obj = json.dumps(data_obj)
        begin_image_number_object = requests.post(
            cfg.NXG_FEC_PARSER_API_URL
            + cfg.NXG_FEC_PARSER_API_VERSION
            + "/image_number",
            data=data_obj,
        )
        begin_image_number_json = begin_image_number_object.json()
        begin_image_num = begin_image_number_json["beginImageNumber"]
        # begin_image_num = 20201109000000
        total_pages, txn_img_json = _paginate_pdf(
            data.get("formType"), file_content, begin_image_num
        )
        txn_img_json = json.dumps(txn_img_json)
        print(total_pages, txn_img_json)

        # Call parser to update JSON tran file
        data_obj = {"submissionId": submission_id, "imageJsonText": txn_img_json}
        requests.put(
            cfg.NXG_FEC_PARSER_API_URL
            + cfg.NXG_FEC_PARSER_API_VERSION
            + "/image_number",
            data=data_obj,
        )
        return begin_image_num


@app.route("parse_next_in_image_generator_queue", methods=["GET"])
def parse_next_in_image_generator_queue():
    """*****************************************************************************************************************
                                 Function to manually run from UI/postman
    *****************************************************************************************************************"""
    if request.method == "GET":
        res = parse_next_in_image_generator_queue()
        return res


def parse_next_in_image_generator_queue():
    """*****************************************************************************************************************
                             Function will get the next report to stamp image on PDF
    ********************************************************************************************************************
        1. Image Generator worker will call this function on a set interval, say every 15 seconds
        2. This Function will read the message from the SQS one at a time and sets the visibility to N number of minutes
           so that other workers will not see it.

        Sample Message
        message_attributes = {'submissionId': {'StringValue': submission_id, 'DataType': 'String'},
                              'committeeId': {'StringValue': committee_id, 'DataType': 'String'},
                              'fileName': {'StringValue': file_name, 'DataType': 'String'},
                              'receivedTime': {'StringValue': str(upload_time), 'DataType': 'String'},
                              'beginImageNumber': {'StringValue': begin_image_number, 'DataType': 'String'}
                              }
    *****************************************************************************************************************"""
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=cfg.IMAGE_GENERATOR_SQS_QUEUE)
    try:
        # Getting One message at a time
        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
            VisibilityTimeout=cfg.MESSAGE_VISIBILITY_TIMEOUT,
        )
    except Exception as e:
        envelope = common.get_return_envelope(
            "false", "unable to read message from image generator queue"
        )
        return flask.jsonify(**envelope), status.HTTP_400_BAD_REQUEST

    # next_image_generator = []
    # next_image_generator.append("one")
    # res = image_generator_data(next_image_generator)
    # print(res)
    # return res
    if len(messages) > 0:
        # Getting the first message
        for message in messages:
            receipt_handle = message.receipt_handle
            # process the messages
            msg_body = message.body
            next_image_generator = []
            print(
                "***************************************************************************************************"
            )
            print("Getting Message from the SQS: " + str(msg_body))
            print(message.message_attributes)
            print(
                "***************************************************************************************************"
            )
            if message.message_attributes is not None:
                next_image_generator.append(
                    {
                        "submissionId": message.message_attributes.get(
                            "submissionId"
                        ).get("StringValue"),
                        "committeeId": message.message_attributes.get(
                            "committeeId"
                        ).get("StringValue"),
                        "fileName": message.message_attributes.get("fileName").get(
                            "StringValue"
                        ),
                        "beginImageNumber": message.message_attributes.get(
                            "beginImageNumber"
                        ).get("StringValue"),
                        "receivedTime": message.message_attributes.get(
                            "receivedTime"
                        ).get("StringValue"),
                    }
                )
                # Parsing the data
                res = image_generator_data(next_image_generator[0])
                message.delete()
                print(res)
                return res
    else:
        print("Nothing to process - Message Queue is empty")
        envelope = common.get_return_envelope(
            "true", "Nothing to process - Message Queue is empty"
        )
        return flask.jsonify(**envelope), status.HTTP_200_OK


def image_generator_data(next_image_generator=None):
    print(next_image_generator)
    submission_id = next_image_generator["submissionId"]
    committee_id = next_image_generator["committeeId"]
    json_file_name = next_image_generator["fileName"]
    begin_image_number = next_image_generator["beginImageNumber"]
    filing_timestamp = next_image_generator["receivedTime"]
    rep_id = json_file_name[0 : json_file_name.index(".json")]
    # rep_id = '8'
    # print(rep_id)

    # image number should not be null, temporarily assigning summy image number
    # if not begin_image_number:
    #     begin_image_number = "20201109000000"
    # begin_image_number = "20201109000000"
    # filing_timestamp = "11/25/2020 1:32PM"
    file_url = (
        "https://" + cfg.AWS_S3_FECFILE_COMPONENTS_DOMAIN + "/output/" + json_file_name
    )
    # file_url = "https://dev-efile-repo.s3.amazonaws.com/" + file_name
    # file_url = "https://dev-efile-repo.s3.amazonaws.com/C00000935_4498f6f2b355426ca127708551e34f2f.json"
    # file_url = 'https://fecfile-dev-components.s3.amazonaws.com/output/8.json'
    # print(file_url)

    file_content = None
    json_data = None
    try:
        with urllib.request.urlopen(file_url) as url:
            file_content = url.read().decode()
        json_data = json.loads(file_content)
    except Exception as e:
        print(e)

    if json_data.get("data"):
        data = json_data.get("data")
        # Stamp PDF
        return _print_pdf(
            data.get("formType"),
            file_content,
            begin_image_number,
            True,
            filing_timestamp,
            None,
            rep_id,
        )
