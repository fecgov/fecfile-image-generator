import flask
import boto3
import re
import os
import pypdftk
import shutil
import pdfkit
import bs4
import urllib.request
import sys
import traceback

from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import common, form

from routes.src.utils import md5_for_text, md5_for_file, directory_files, error


def print_f99_pdftk_html(
    stamp_print="",
    paginate=False,
    begin_image_num=None,
    page_count=False,
    file_content=None,
    silent_print=False,
    filing_timestamp=None,
    rep_id=None,
    attachment_file_content=None,
):
    # check if json_file is in the request
    # HTML("templates/forms/test.html").write_pdf("output/pdf/test/test.pdf")
    # HTML(string='''<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><div><b>This is bold text</b></div><div><u>This is underline text</u></div><div><i>This is italics text</i><u><br></u></div><div align='center'><u>Title</u></div><div align='left'><u><br></u></div><ol><li>one</li><li>two</li><li>three</li></ol>''').write_pdf("output/pdf/test/test.pdf")
    # pdfkit.from_file("templates/forms/test.html", "output/pdf/test/test.pdf")
    # pypdftk.stamp(current_app.config['FORM_TEMPLATES_LOCATION'].format('F99'), "output/pdf/test/test.pdf", "output/pdf/test/output.pdf")
    try:
        silent_print = silent_print
        txn_img_num = begin_image_num
        filing_timestamp = filing_timestamp

        if (
            (page_count and file_content)
            or ((paginate or silent_print) and file_content and begin_image_num)
            or (not paginate and "json_file" in request.files)
        ):

            if page_count and file_content:
                json_file_md5 = md5_for_text(file_content)
                json_data = json.loads(file_content)

            elif (paginate or silent_print) and file_content and begin_image_num:
                # generate md5 for file_content
                json_file_md5 = md5_for_text(file_content)
                json_data = json.loads(file_content)

            elif not paginate and "json_file" in request.files:
                json_file = request.files.get("json_file")
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
                json_data = json.load(
                    open(
                        current_app.config["REQUEST_FILE_LOCATION"].format(
                            json_file_md5
                        )
                    )
                )

            md5_directory = current_app.config["OUTPUT_DIR_LOCATION"].format(
                json_file_md5
            )

            # if paginate or page_count is True and directory exist then don't remove it
            is_dir_exist = False
            if os.path.isdir(md5_directory):
                is_dir_exist = True

            os.makedirs(md5_directory, exist_ok=True)
            # os.makedirs(md5_directory + "images", exist_ok=True)
            if not os.path.exists(md5_directory + "images"):
                shutil.copytree("templates/forms/F99/images", md5_directory + "images")
            shutil.copyfile(
                "templates/forms/F99/form-text.css", md5_directory + "form-text.css"
            )
            infile = current_app.config["HTML_FORM_TEMPLATES_LOCATION"].format(
                "template"
            )
            outfile = md5_directory + json_file_md5 + ".html"

            form99_json_data = json_data["data"]

            with open(infile) as inf:
                txt = inf.read()
                soup = bs4.BeautifulSoup(txt, features="html5lib")
                soup.find(
                    "label", attrs={"id": "committeeName"}
                ).string = form99_json_data["committeeName"]
                soup.find("label", attrs={"id": "street1"}).string = form99_json_data[
                    "street1"
                ]
                soup.find("label", attrs={"id": "street2"}).string = form99_json_data[
                    "street2"
                ]
                soup.find("label", attrs={"id": "city"}).string = form99_json_data[
                    "city"
                ]
                soup.find("label", attrs={"id": "state"}).string = form99_json_data[
                    "state"
                ]
                soup.find("label", attrs={"id": "zipCode"}).string = form99_json_data[
                    "zipCode"
                ]
                soup.find(
                    "span", attrs={"id": "committeeId"}
                ).string = form99_json_data["committeeId"]

                name_list = ["LastName", "FirstName", "MiddleName", "Prefix", "Suffix"]

                treasurerFullName = ""
                for item in name_list:
                    item = "treasurer" + item
                    if form99_json_data.get(item):
                        treasurerFullName += form99_json_data.get(item) + ", "
                soup.find(
                    "label", attrs={"id": "treasurerFullName"}
                ).string = treasurerFullName[:-2]

                soup.find("label", attrs={"id": "treasurerName"}).string = (
                    (
                        form99_json_data.get("treasurerLastName", "")
                        + ", "
                        + form99_json_data.get("treasurerFirstName", "")
                    )
                    .strip()
                    .rstrip(",")
                    .strip()
                )

                f99_html_data = form99_json_data["text"]
                soup.find("label", attrs={"id": "text"}).string = f99_html_data
                soup.find(
                    "label", attrs={"id": form99_json_data["reason"]}
                ).string = "X"

                date_array = form99_json_data["dateSigned"].split("/")
                soup.find("span", attrs={"id": "dateSignedMonth"}).string = str(
                    date_array[0]
                )
                soup.find("span", attrs={"id": "dateSignedDate"}).string = str(
                    date_array[1]
                )
                soup.find("span", attrs={"id": "dateSignedYear"}).string = str(
                    date_array[2]
                )

                with open(outfile, "w") as output_file:
                    output_file.write(
                        str(soup).replace("&lt;", "<").replace("&gt;", ">")
                    )

                # F99 PDF page padding options
                options = {
                    "margin-top": "0.40in",
                    "margin-right": "0.20in",
                    "margin-bottom": "0.40in",
                    "margin-left": "0.20in",
                }

                # HTML(outfile).write_pdf(md5_directory + json_file_md5 + '.pdf', stylesheets=[CSS(current_app.config['FORMS_LOCATION'].format('F99.css'))])
                pdfkit.from_file(
                    outfile, md5_directory + json_file_md5 + ".pdf", options=options
                )
                # pdfkit.from_file(outfile, md5_directory + json_file_md5 + '.pdf')

                total_no_of_pages = pypdftk.get_num_pages(
                    md5_directory + json_file_md5 + ".pdf"
                )

            # checking if attachment_file exist
            if ((paginate or page_count) and attachment_file_content) or (
                not paginate and "attachment_file" in request.files
            ):
                # reading Attachment title file
                attachment_title_file = current_app.config[
                    "FORM_TEMPLATES_LOCATION"
                ].format("Attachment_Title")

                if (paginate or page_count) and attachment_file_content:
                    attachment_file = json.loads(attachment_file_content)
                else:
                    attachment_file = request.files.get("attachment_file")

                attachment_file.save(
                    os.path.join(md5_directory + "attachment_temp.pdf")
                )
                os.makedirs(md5_directory + "attachment", exist_ok=True)
                os.makedirs(md5_directory + "final_attachment", exist_ok=True)
                pypdftk.split(
                    md5_directory + "attachment_temp.pdf", md5_directory + "attachment"
                )
                os.remove(md5_directory + "attachment/doc_data.txt")
                attachment_no_of_pages = pypdftk.get_num_pages(
                    os.path.join(md5_directory + "attachment_temp.pdf")
                )
                attachment_page_no = total_no_of_pages
                total_no_of_pages += attachment_no_of_pages

                # we are doing this to assign page numbers to attachment file
                for filename in os.listdir(md5_directory + "attachment"):
                    attachment_page_no += 1
                    page_dict = {}
                    page_dict["PAGESTR"] = (
                        "PAGE "
                        + str(attachment_page_no)
                        + " / "
                        + str(total_no_of_pages)
                    )

                    if silent_print:
                        page_dict["IMGNO"] = txn_img_num + attachment_page_no

                    pypdftk.fill_form(
                        attachment_title_file,
                        md5_directory
                        + "attachment/attachment_page_"
                        + str(attachment_page_no)
                        + ".pdf",
                    )
                    pypdftk.stamp(
                        md5_directory + "attachment/" + filename,
                        md5_directory
                        + "attachment/attachment_page_"
                        + str(attachment_page_no)
                        + ".pdf",
                        md5_directory
                        + "final_attachment/attachment_"
                        + str(attachment_page_no)
                        + ".pdf",
                    )
                pypdftk.concat(
                    directory_files(md5_directory + "final_attachment/"),
                    md5_directory + "attachment.pdf",
                )
                os.remove(md5_directory + "attachment_temp.pdf")

            os.makedirs(md5_directory + "pages", exist_ok=True)
            os.makedirs(md5_directory + "final_pages", exist_ok=True)
            pypdftk.split(
                md5_directory + json_file_md5 + ".pdf", md5_directory + "pages"
            )
            os.remove(md5_directory + "pages/doc_data.txt")

            f99_page_no = 1
            for filename in os.listdir(md5_directory + "pages"):
                page_dict = {}
                page_dict["PAGESTR"] = (
                    "PAGE " + str(f99_page_no) + " / " + str(total_no_of_pages)
                )

                if silent_print:
                    page_dict["IMGNO"] = txn_img_num
                    txn_img_num += 1
                    # need to print timestamp on first page only
                    if filing_timestamp and f99_page_no == 1:
                        page_dict["FILING_TIMESTAMP"] = filing_timestamp

                page_number_file = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                    "Page_Number"
                )
                pypdftk.fill_form(
                    page_number_file,
                    page_dict,
                    md5_directory
                    + "pages/page_number_"
                    + str(f99_page_no).zfill(6)
                    + ".pdf",
                )
                pypdftk.stamp(
                    md5_directory
                    + "pages/page_number_"
                    + str(f99_page_no).zfill(6)
                    + ".pdf",
                    md5_directory + "pages/" + filename,
                    md5_directory
                    + "final_pages/page_"
                    + str(f99_page_no).zfill(6)
                    + ".pdf",
                )
                f99_page_no += 1

            pypdftk.concat(
                directory_files(md5_directory + "final_pages/"),
                json_file_md5 + "_temp.pdf",
            )

            if ((paginate or page_count) and attachment_file_content) or (
                not paginate and "attachment_file" in request.files
            ):
                pypdftk.concat(
                    [json_file_md5 + "_temp.pdf", md5_directory + "attachment.pdf"],
                    md5_directory + "all_pages.pdf",
                )
                shutil.rmtree(md5_directory + "attachment")
                shutil.rmtree(md5_directory + "final_attachment")
                os.remove(md5_directory + "attachment.pdf")
            else:
                shutil.move(
                    json_file_md5 + "_temp.pdf", md5_directory + "all_pages.pdf"
                )

            # clean up task
            shutil.rmtree(md5_directory + "pages")
            shutil.rmtree(md5_directory + "final_pages")
            os.remove(md5_directory + json_file_md5 + ".pdf")

            # if flask.request.method == "POST":

            response = {
                # 'file_name': ent_app.conf'{}.pdf'.format(json_file_md5),
                "total_pages": total_no_of_pages,
            }

            if not page_count and not paginate:
                s3 = boto3.client("s3")
                extraArgs = {"ContentType": "application/pdf", "ACL": "public-read"}

                if silent_print:
                    response["pdf_url"] = current_app.config['S3_FILE_URL'] + rep_id + '.pdf'
                    s3.upload_file(
                        md5_directory + 'all_pages.pdf',
                        current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                        current_app.config['AWS_FECFILE_OUTPUT_DIRECTORY'] + '/' +
                        str(rep_id) + '.pdf',
                        ExtraArgs=extraArgs)
                else:
                    response["pdf_url"] = (
                        current_app.config["PRINT_OUTPUT_FILE_URL"].format(
                            json_file_md5
                        )
                        + "all_pages.pdf",
                    )

                    s3.upload_file(
                        md5_directory + "all_pages.pdf",
                        current_app.config["AWS_FECFILE_COMPONENTS_BUCKET_NAME"],
                        md5_directory + "all_pages.pdf",
                        ExtraArgs=extraArgs,
                    )
            else:
                if not is_dir_exist:
                    shutil.rmtree(md5_directory)
                if paginate:
                    txn_img_json = {
                        "summary": {
                            "committeeId": form99_json_data.get("committeeId", None),
                            "begin_image_num": begin_image_num,
                            "end_image_num": txn_img_num
                        }
                    }
                    response["txn_img_json"] = txn_img_json

            envelope = common.get_return_envelope(data=response)
            status_code = (
                status.HTTP_200_OK
                if page_count or paginate
                else status.HTTP_201_CREATED
            )
            return flask.jsonify(**envelope), status_code

            # elif page_count or paginate:
            #     if not is_dir_exist:
            #         shutil.rmtree(md5_directory)
            #         response = {
            #             "total_pages": total_no_of_pages,
            #         }
            #     elif paginate:
            #         txn_img_json = {
            #             'summary' : {
            #                 'committeeId': form99_json_data.get('committeeId', None)
            #             }
            #         }
            #         response['txn_img_json'] = txn_img_json
            #     return True, response
            # elif silent_print and not flask.request.method == "POST":
            #     return True, {}
        else:
            if paginate or page_count or silent_print:
                envelope = common.get_return_envelope(False, "")
            else:
                # elif flask.request.method == "POST":
                envelope = common.get_return_envelope(
                    False, "json_file is missing from your request"
                )
            return flask.jsonify(**envelope), status.HTTP_400_BAD_REQUEST
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        return error("Error generating print preview, error message: " + str(e))
