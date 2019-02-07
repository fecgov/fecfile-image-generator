import flask
import boto3

from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import tmoflask, utils, common, form
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject


def print_f99():
    """
    This function is being invoked internally from controllers
    HTTP request needs to have form_type, file, and attachment_file
    form_type : F99
    json_file: please refer to below sample JSON
    attachment_file: It is a PDF file that will be merged to the generated PDF file.
    sample:
    {
    "REASON_TYPE":"MST",
    "COMMITTEE_NAME":"DONALD J. TRUMP FOR PRESIDENT, INC.",
    "FILER_FEC_ID_NUMBER":"C00580100",
    "IMGNO":"201812179143565008",
    "FILING_TIMESTAMP":"12/17/2018 17 : 09",
    "STREET_1":"725 FIFTH AVENUE",
    "STREET_2":"",
    "CITY":"NEW YORK",
    "STATE":"NY",
    "ZIP":"10022",
    "TREASURER_FULL_NAME":"CRATE, BRADLEY, , ,",
    "TREASURER_NAME":"CRATE, BRADLEY, , ,",
    "EF_STAMP":"[Electronically Filed]",
    "DATE_SIGNED_MM":"01",
    "DATE_SIGNED_DD":"28",
    "DATE_SIGNED_YY":"2019",
    "MISCELLANEOUS_TEXT":"This statement is in response to the Commission's letter to the Committee
                            dated November 12, 2018, regarding two items related to the
                            above-referenced report ('the Original Report')."
    }
    :return: return JSON response
    sample:
    {
    "message": "",
    "results": {
        "file_name": "bd78435a70a70d656145dae89e0e22bb.pdf",
        "file_url": "https://fecfile-dev-components.s3.amazonaws.com/output/bd78435a70a70d656145dae89e0e22bb.pdf"
    },
    "success": "true"
    }
    """
    if 'json_file' in request.files:
        json_file = request.files.get('json_file')
        json_file_md5 = utils.md5_for_file(json_file)
        json_file.stream.seek(0)

        infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F99')
        json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
        outfile = current_app.config['OUTPUT_FILE_LOCATION'].format(json_file_md5)

        json_data = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))

        # json_data['FILER_FEC_ID_NUMBER'] = json_data['FILER_FEC_ID_NUMBER'][1:]

        if json_data['REASON_TYPE'] == 'MST':
            reason_type_data = {"REASON_TYPE_MST": "/MST"}

        if json_data['REASON_TYPE'] == 'MSM':
            reason_type_data = {"REASON_TYPE_MSM": "/MSM"}

        if json_data['REASON_TYPE'] == 'MSI':
            reason_type_data = {"REASON_TYPE_MSI": "/MSI"}

        if json_data['REASON_TYPE'] == 'MSW':
            reason_type_data = {"REASON_TYPE_MSW": "/MSW"}
        # open the input file

        input_stream = open(infile, "rb")

        pdf_reader = PdfFileReader(input_stream, strict=True)

        if "/AcroForm" in pdf_reader.trailer["/Root"]:
            pdf_reader.trailer["/Root"]["/AcroForm"].update(

                {NameObject("/NeedAppearances"): BooleanObject(True)})

        pdf_writer = PdfFileWriter()

        form.set_need_appearances_writer(pdf_writer)

        if "/AcroForm" in pdf_writer._root_object:
            pdf_writer._root_object["/AcroForm"].update(
                {NameObject("/NeedAppearances"): BooleanObject(True)})

        for page_num in range(pdf_reader.numPages):
            page_obj = pdf_reader.getPage(page_num)

            pdf_writer.addPage(page_obj)

            form.update_checkbox_values(page_obj, reason_type_data)

            pdf_writer.updatePageFormFieldValues(page_obj, json_data)

        # Add the F99 attachment
        if 'attachment_file' in request.files:
            # reading Attachment title file
            attachment_title_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('Attachment_Title')
            attachment_title_stream = open(attachment_title_file, "rb")
            attachment_title_reader = PdfFileReader(attachment_title_stream, strict=True)
            attachment_stream = request.files.get('attachment_file')
            attachment_reader = PdfFileReader(attachment_stream, strict=True)

            for attachment_page_num in range(attachment_reader.numPages):
                attachment_page_obj = attachment_reader.getPage(attachment_page_num)
                if attachment_page_num == 0:
                    attachment_page_obj.mergePage(attachment_title_reader.getPage(0))

                pdf_writer.addPage(attachment_page_obj)

        output_stream = open(outfile, "wb")

        pdf_writer.write(output_stream)

        input_stream.close()

        output_stream.close()

        # push output file to AWS
        s3 = boto3.client('s3')
        s3.upload_file(outfile, current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                       current_app.config['OUTPUT_FILE_LOCATION'].format(json_file_md5),
                       ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})

        response = {
            # 'file_name': '{}.pdf'.format(json_file_md5),
            'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5)
        }

        if flask.request.method == "POST":
            envelope = common.get_return_envelope(
                data=response
            )
            status_code = status.HTTP_201_CREATED
            return flask.jsonify(**envelope), status_code
    else:

        if flask.request.method == "POST":
            envelope = common.get_return_envelope(
                'false', 'JSON file is missing from your request'
            )
            status_code = status.HTTP_400_BAD_REQUEST
            return flask.jsonify(**envelope), status_code

