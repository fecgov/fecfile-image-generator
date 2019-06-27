import flask
import boto3
import re
import os
import pypdftk
import shutil
import pdfkit
import bs4

from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import tmoflask, utils, common, form
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject


def split_f99_text_pages(json_data):
    f99_page_data = {}
    f99_additional_page_data = []
    f99_text = json_data['MISCELLANEOUS_TEXT']
    lines_count = 0
    main_page_data = ''
    additional_pages = 0
    additional_page_data = ''
    match_count = 0
    for line in f99_text.splitlines(True):
        lines_count += 1
        if len(line) > 117:
            (line, match_count) = re.subn("(.{1,117})( +|$)\n?|(.{117})", "\\1\\3^\n", line, match_count, re.DOTALL)
            lines_count += match_count
        if lines_count <= 17:
            line = line.replace('^\n', ' ')
            main_page_data = main_page_data + line
        else:
            temp_lines_count = lines_count - match_count
            if temp_lines_count <= 17:

                for temp_line in line.splitlines(True):
                    temp_lines_count += 1
                    if temp_lines_count <= 17:
                        temp_line = temp_line.replace('^\n', ' ')
                        main_page_data = main_page_data + temp_line
                    else:
                        additional_page_data = additional_page_data + temp_line
            else:
                additional_page_data = additional_page_data + line
    f99_page_data["main_page"] = main_page_data
    if lines_count > 17:
        additional_pages_reminder = (lines_count - 17) % 49
        if additional_pages_reminder != 0:
            additional_pages = ((lines_count - 17) // 49) + 1
    additional_lines = additional_page_data.splitlines(True)

    for additional_page_number in range(additional_pages):
        start = (49 * (additional_page_number))
        end = (49 * (additional_page_number + 1)) - 1
        additional_lines_str = "".join(map(str, additional_lines[start:end]))
        additional_lines_str = additional_lines_str.replace('^\n', ' ')
        additional_page_dict = {additional_page_number: additional_lines_str}
        f99_additional_page_data.append(additional_page_dict)

    f99_page_data["additional_pages"] = f99_additional_page_data
    # convert to json data
    f99_page_data_json = json.dumps(f99_page_data)
    return f99_page_data_json


def split_f99_text_pages_html(json_data):
    f99_page_data = {}
    f99_additional_page_data = []
    f99_text = json_data['MISCELLANEOUS_TEXT']
    lines_count = 0
    main_page_data = ''
    additional_pages = 0
    additional_page_data = ''
    match_count = 0
    for line in f99_text.splitlines(True):
        lines_count += 1
        if len(line) > 117:
            (line, match_count) = re.subn("(.{1,117})( +|$)<br>?|(.{117})", "\\1\\3^<br>", line, match_count, re.DOTALL)
            lines_count += match_count
        if lines_count <= 17:
            line = line.replace('^<br>', ' ')
            main_page_data = main_page_data + line
        else:
            temp_lines_count = lines_count - match_count
            if temp_lines_count <= 17:

                for temp_line in line.splitlines(True):
                    temp_lines_count += 1
                    if temp_lines_count <= 17:
                        temp_line = temp_line.replace('^<br>', ' ')
                        main_page_data = main_page_data + temp_line
                    else:
                        additional_page_data = additional_page_data + temp_line
            else:
                additional_page_data = additional_page_data + line
    f99_page_data["main_page"] = main_page_data
    if lines_count > 17:
        additional_pages_reminder = (lines_count - 17) % 49
        if additional_pages_reminder != 0:
            additional_pages = ((lines_count - 17) // 49) + 1
    additional_lines = additional_page_data.splitlines(True)

    for additional_page_number in range(additional_pages):
        start = (49 * (additional_page_number))
        end = (49 * (additional_page_number + 1)) - 1
        additional_lines_str = "".join(map(str, additional_lines[start:end]))
        additional_lines_str = additional_lines_str.replace('^<br>', ' ')
        additional_page_dict = {additional_page_number: additional_lines_str}
        f99_additional_page_data.append(additional_page_dict)

    f99_page_data["additional_pages"] = f99_additional_page_data
    # convert to json data
    f99_page_data_json = json.dumps(f99_page_data)
    return f99_page_data_json

# def split_f99_text_pages(json_data):
#     f99_page_data = {}
#     f99_additional_page_data = []
#     f99_text = json_data['MISCELLANEOUS_TEXT']
#     lines_count = 0
#     main_page_data = ''
#     additional_pages = 0
#     additional_page_data = ''
#     match_count = 0
#     for line in f99_text.splitlines(True):
#         lines_count += 1
#         if len(line) > 117:
#             lines_count += 1
#             (line, match_count) = re.subn("(.{1,117})( +|$)\n?|(.{117})", "\\1^\n", line, match_count, re.DOTALL)
#             lines_count += match_count
#             if lines_count > 17:
#                 temp_lines_count = 0
#                 for temp_line in line.splitlines(True):
#                     temp_lines_count += 1
#                     if temp_lines_count <= 17:
#                         temp_line = temp_line.replace('^\n', ' ')
#                         main_page_data = main_page_data + temp_line
#                     else:
#                         additional_page_data = additional_page_data + temp_line
#         if lines_count <= 17:
#             line = line.replace('^\n', ' ')
#             main_page_data = main_page_data + line
#         else:
#             additional_page_data = additional_page_data + line
#     f99_page_data["main_page"] = main_page_data
#     if lines_count > 17:
#         additional_pages_reminder = (lines_count - 17) % 49
#         if additional_pages_reminder != 0:
#             additional_pages = ((lines_count - 17) // 49) + 1
#     additional_lines = additional_page_data.splitlines(True)
#
#     for additional_page_number in range(additional_pages):
#         start = (49 * (additional_page_number))
#         end = (49 * (additional_page_number + 1)) - 1
#         additional_lines_str = "".join(map(str, additional_lines[start:end]))
#         additional_lines_str = additional_lines_str.replace('^\n', ' ')
#         additional_page_dict = {additional_page_number: additional_lines_str}
#         f99_additional_page_data.append(additional_page_dict)
#
#     f99_page_data["additional_pages"] = f99_additional_page_data
#     # convert to json data
#     f99_page_data_json = json.dumps(f99_page_data)
#     return f99_page_data_json

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


def directory_files(directory):
    files_list = []
    file_names = sorted(os.listdir(directory))
    for file_name in file_names:
        files_list.append(directory+file_name)
    return files_list


def print_f99_pdftk(stamp_print):
    # check if json_file is in the request

    if 'json_file' in request.files:
        total_no_of_pages = 1
        page_no = 1
        json_file = request.files.get('json_file')
        # generate md5 for json file
        json_file_md5 = utils.md5_for_file(json_file)
        json_file.stream.seek(0)
        md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
        os.makedirs(md5_directory, exist_ok=True)
        infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F99')
        # save json file as md5 file name
        json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
        outfile = md5_directory+json_file_md5+'_temp.pdf'
        json_data = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
        # setting timestamp and imgno to empty as these needs to show up after submission
        if stamp_print != 'stamp':
            json_data['FILING_TIMESTAMP'] = ''
            json_data['IMGNO'] = ''

        f99_pages_text_json = json.loads(split_f99_text_pages(json_data))
        json_data['MISCELLANEOUS_TEXT'] = f99_pages_text_json['main_page']
        total_no_of_pages += len(f99_pages_text_json['additional_pages'])
        # checking if attachment_file exist
        if 'attachment_file' in request.files:
            # reading Attachment title file
            attachment_title_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('Attachment_Title')
            attachment_file = request.files.get('attachment_file')
            attachment_file.save(os.path.join(md5_directory + 'attachment_temp.pdf'))
            os.makedirs(md5_directory + 'attachment', exist_ok=True)
            os.makedirs(md5_directory + 'final_attachment', exist_ok=True)
            pypdftk.split(md5_directory + 'attachment_temp.pdf', md5_directory+'attachment')
            os.remove(md5_directory + 'attachment/doc_data.txt')
            attachment_no_of_pages = pypdftk.get_num_pages(os.path.join(md5_directory + 'attachment_temp.pdf'))
            attachment_page_no = total_no_of_pages
            total_no_of_pages += attachment_no_of_pages

            # we are doing this to assign page numbers to attachment file
            for filename in os.listdir(md5_directory+'attachment'):
                attachment_page_no += 1
                pypdftk.fill_form(attachment_title_file, {"PAGESTR": "PAGE " + str(attachment_page_no) + " / " + str(total_no_of_pages)},
                                md5_directory +'attachment/attachment_page_'+str(attachment_page_no)+'.pdf')
                pypdftk.stamp(md5_directory+'attachment/'+filename, md5_directory +
                              'attachment/attachment_page_'+str(attachment_page_no)+'.pdf', md5_directory +
                              'final_attachment/attachment_'+str(attachment_page_no)+'.pdf')
            pypdftk.concat(directory_files(md5_directory +'final_attachment/'), md5_directory + 'attachment.pdf')
            os.remove(md5_directory + 'attachment_temp.pdf')
            shutil.rmtree(md5_directory + 'attachment')
            shutil.rmtree(md5_directory + 'final_attachment')

        json_data['PAGESTR'] = "PAGE " + str(page_no) + " / " + str(total_no_of_pages)

        pypdftk.fill_form(infile, json_data, outfile, flatten=False)
        additional_page_counter = 0
        if len(f99_pages_text_json['additional_pages']) > 0:
            continuation_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('F99_CONT')
            os.makedirs(md5_directory + 'merge', exist_ok=True)
            for additional_page in f99_pages_text_json['additional_pages']:
                page_no += 1
                continuation_outfile = md5_directory + 'merge/' + str(additional_page_counter)+'.pdf'
                pypdftk.fill_form(continuation_file, {"PAGESTR": "PAGE "+str(page_no)+" / " + str(total_no_of_pages),
                                                      "CONTINOUS_TEXT": additional_page[str(additional_page_counter)]}, continuation_outfile)
                pypdftk.concat([outfile, continuation_outfile], md5_directory + json_file_md5 + '_all_pages_temp.pdf')
                shutil.copy(md5_directory + json_file_md5 + '_all_pages_temp.pdf', outfile)
                additional_page_counter += 1
                os.remove(md5_directory + json_file_md5 + '_all_pages_temp.pdf')

        # Add the F99 attachment
        if 'attachment_file' in request.files:
            pypdftk.concat([outfile, md5_directory + 'attachment.pdf'], md5_directory + 'all_pages.pdf')
            os.remove(md5_directory + 'attachment.pdf')
        else:
            shutil.copy(outfile, md5_directory + 'all_pages.pdf')
        os.remove(md5_directory + json_file_md5 +'_temp.pdf')
        # push output file to AWS
        s3 = boto3.client('s3')
        s3.upload_file(md5_directory + 'all_pages.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                       md5_directory+'all_pages.pdf',ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
        response = {
            # 'file_name': '{}.pdf'.format(json_file_md5),
            'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5)+'all_pages.pdf'
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


def print_f99_pdftk_html(stamp_print):
    # check if json_file is in the request
    # HTML("templates/forms/test.html").write_pdf("output/pdf/test/test.pdf")
    # HTML(string='''<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><div><b>This is bold text</b></div><div><u>This is underline text</u></div><div><i>This is italics text</i><u><br></u></div><div align='center'><u>Title</u></div><div align='left'><u><br></u></div><ol><li>one</li><li>two</li><li>three</li></ol>''').write_pdf("output/pdf/test/test.pdf")
    # pdfkit.from_file("templates/forms/test.html", "output/pdf/test/test.pdf")
    # pypdftk.stamp(current_app.config['FORM_TEMPLATES_LOCATION'].format('F99'), "output/pdf/test/test.pdf", "output/pdf/test/output.pdf")



    if 'json_file' in request.files:
        total_no_of_pages = 1
        page_no = 1
        json_file = request.files.get('json_file')
        # generate md5 for json file
        json_file_md5 = utils.md5_for_file(json_file)
        json_file.stream.seek(0)
        md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
        os.makedirs(md5_directory, exist_ok=True)
        # os.makedirs(md5_directory + "images", exist_ok=True)
        if not os.path.exists(md5_directory + "images"):
            shutil.copytree("templates/forms/F99/images", md5_directory + "images")
        shutil.copyfile("templates/forms/F99/form-text.css", md5_directory + "form-text.css")
        infile = current_app.config['HTML_FORM_TEMPLATES_LOCATION'].format('template')
        json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
        outfile = md5_directory + json_file_md5 + '.html'
        json_data = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
        form99_json_data = json_data['data']
        # load the file
        with open(infile) as inf:
            txt = inf.read()
            soup = bs4.BeautifulSoup(txt)
            soup.find('label', attrs={'id': 'committeeName'}).string = form99_json_data['committeeName']
            soup.find('label', attrs={'id': 'street1'}).string = form99_json_data['street1']
            soup.find('label', attrs={'id': 'street2'}).string = form99_json_data['street2']
            soup.find('label', attrs={'id': 'city'}).string = form99_json_data['city']
            soup.find('label', attrs={'id': 'state'}).string = form99_json_data['state']
            soup.find('label', attrs={'id': 'zipCode'}).string = form99_json_data['zipCode']
            soup.find('span', attrs={'id': 'committeeId'}).string = form99_json_data['committeeId']
            soup.find('label', attrs={'id': 'treasurerFullName'}).string = form99_json_data['treasurerLastName'] + \
                                                                           ', ' + form99_json_data['treasurerFirstName'] \
                                                                           + ', ' + form99_json_data['treasurerMiddleName'] \
                                                                           + ', ' + form99_json_data['treasurerPrefix'] \
                                                                           + ', ' + form99_json_data['treasurerSuffix']
            soup.find('label', attrs={'id': 'treasurerName'}).string = form99_json_data['treasurerLastName'] + \
                                                                       ', ' + form99_json_data['treasurerFirstName']
            f99_html_data = form99_json_data['text']
            soup.find('label', attrs={'id': 'text'}).string = f99_html_data
            soup.find('label', attrs={'id': form99_json_data['reason']}).string = 'X'

            date_array = form99_json_data['dateSigned'].split("/")
            soup.find('span', attrs={'id': 'dateSignedMonth'}).string = str(date_array[0])
            soup.find('span', attrs={'id': 'dateSignedDate'}).string = str(date_array[1])
            soup.find('span', attrs={'id': 'dateSignedYear'}).string = str(date_array[2])


            with open(outfile, "w") as output_file:
                output_file.write(str(soup).replace("&lt;", "<").replace("&gt;", ">"))

            # F99 PDF page padding options
            # options = {
            #     'margin-top': '0.36in',
            #     'margin-right': '0.25in',
            #     'margin-bottom': '0.39in',
            #     'margin-left': '0.25in'
            # }
            options = {
                'margin-top': '0.40in',
                'margin-right': '0.20in',
                'margin-bottom': '0.40in',
                'margin-left': '0.20in'
            }
            # HTML(outfile).write_pdf(md5_directory + json_file_md5 + '.pdf', stylesheets=[CSS(current_app.config['FORMS_LOCATION'].format('F99.css'))])
            pdfkit.from_file(outfile, md5_directory + json_file_md5 + '.pdf', options=options)
            # pdfkit.from_file(outfile, md5_directory + json_file_md5 + '.pdf')

            total_no_of_pages = pypdftk.get_num_pages(md5_directory + json_file_md5 + '.pdf')
            page_number_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('Page_Number')



        # checking if attachment_file exist
        if 'attachment_file' in request.files:
            # reading Attachment title file
            attachment_title_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('Attachment_Title')
            attachment_file = request.files.get('attachment_file')
            attachment_file.save(os.path.join(md5_directory + 'attachment_temp.pdf'))
            os.makedirs(md5_directory + 'attachment', exist_ok=True)
            os.makedirs(md5_directory + 'final_attachment', exist_ok=True)
            pypdftk.split(md5_directory + 'attachment_temp.pdf', md5_directory+'attachment')
            os.remove(md5_directory + 'attachment/doc_data.txt')
            attachment_no_of_pages = pypdftk.get_num_pages(os.path.join(md5_directory + 'attachment_temp.pdf'))
            attachment_page_no = total_no_of_pages
            total_no_of_pages += attachment_no_of_pages

            # we are doing this to assign page numbers to attachment file
            for filename in os.listdir(md5_directory+'attachment'):
                attachment_page_no += 1
                pypdftk.fill_form(attachment_title_file, {"PAGESTR": "PAGE " + str(attachment_page_no) + " / " + str(total_no_of_pages)},
                                md5_directory +'attachment/attachment_page_'+str(attachment_page_no)+'.pdf')
                pypdftk.stamp(md5_directory+'attachment/'+filename, md5_directory +
                              'attachment/attachment_page_'+str(attachment_page_no)+'.pdf', md5_directory +
                              'final_attachment/attachment_'+str(attachment_page_no)+'.pdf')
            pypdftk.concat(directory_files(md5_directory +'final_attachment/'), md5_directory + 'attachment.pdf')
            os.remove(md5_directory + 'attachment_temp.pdf')
            # shutil.rmtree(md5_directory + 'attachment')
            # shutil.rmtree(md5_directory + 'final_attachment')
            # pypdftk.concat([md5_directory + json_file_md5 + '.pdf', md5_directory + 'attachment.pdf'], md5_directory + 'all_pages_temp.pdf')
        # else:
        #     shutil.move(md5_directory + json_file_md5 + '.pdf', md5_directory + 'all_pages_temp.pdf')
        os.makedirs(md5_directory + 'pages', exist_ok=True)
        os.makedirs(md5_directory + 'final_pages', exist_ok=True)
        pypdftk.split(md5_directory + json_file_md5 + '.pdf', md5_directory + 'pages')
        os.remove(md5_directory + 'pages/doc_data.txt')
        f99_page_no = 1
        for filename in os.listdir(md5_directory + 'pages'):
            pypdftk.fill_form(page_number_file,
                              {"PAGESTR": "PAGE " + str(f99_page_no) + " / " + str(total_no_of_pages)},
                              md5_directory + 'pages/page_number_' + str(f99_page_no) + '.pdf')
            pypdftk.stamp(md5_directory +
                          'pages/page_number_' + str(f99_page_no) + '.pdf', md5_directory + 'pages/' + filename, md5_directory +
                          'final_pages/page_' + str(f99_page_no) + '.pdf')
            f99_page_no += 1

        pypdftk.concat(directory_files(md5_directory + 'final_pages/'), json_file_md5 + '_temp.pdf')

        if 'attachment_file' in request.files:
            pypdftk.concat([json_file_md5 + '_temp.pdf', md5_directory + 'attachment.pdf'], md5_directory + 'all_pages.pdf')
            shutil.rmtree(md5_directory + 'attachment')
            shutil.rmtree(md5_directory + 'final_attachment')
            os.remove(md5_directory + 'attachment.pdf')
        else:
            shutil.move(json_file_md5 + '_temp.pdf', md5_directory + 'all_pages.pdf')

        # clean up task
        shutil.rmtree(md5_directory + 'pages')
        shutil.rmtree(md5_directory + 'final_pages')
        # os.remove(md5_directory + json_file_md5 + '.html')
        # shutil.rmtree(md5_directory + 'images')
        # os.remove(md5_directory + 'form-text.css')
        os.remove(md5_directory + json_file_md5 + '.pdf')



        # for f99_page_no in range(f99_no_of_pages):
        #     pypdftk.fill_form(page_number_file,
        #                   {"PAGESTR": "PAGE " + str(f99_page_no+1) + " / " + str(total_no_of_pages)},
        #                   md5_directory + 'pages/page_' + str(f99_page_no+1) + '.pdf')
        #     pypdftk.stamp(md5_directory + json_file_md5 + '.pdf', md5_directory +
        #                   'pages/page_' + str(f99_page_no+1) + '.pdf', md5_directory + json_file_md5 + '_temp.pdf')

        # json_data['PAGESTR'] = "PAGE " + str(page_no) + " / " + str(total_no_of_pages)

        # json_data['MISCELLANEOUS_TEXT'] = ''
        # xfdf_path = pypdftk.gen_xfdf(json_data)
        # pypdftk.fill_form(infile, json_data, outfile)


        # HTML(string='''<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><font face='Helvetica' size=10 ''' + f99_full_text).\
        #     write_pdf("output/pdf/test/test.pdf")
        # pypdftk.stamp(outfile, "output/pdf/test/test.pdf", "output/pdf/test/output.pdf")

        # additional_page_counter = 0
        # if len(f99_pages_text_json['additional_pages']) > 0:
        #     continuation_file = current_app.config['FORM_TEMPLATES_LOCATION'].format('F99_CONT')
        #     os.makedirs(md5_directory + 'merge', exist_ok=True)
        #     for additional_page in f99_pages_text_json['additional_pages']:
        #         page_no += 1
        #         continuation_outfile = md5_directory + 'merge/' + str(additional_page_counter)+'.pdf'
        #         pypdftk.fill_form(continuation_file, {"PAGESTR": "PAGE "+str(page_no)+" / " + str(total_no_of_pages),
        #                                               "CONTINOUS_TEXT": additional_page[str(additional_page_counter)]}, continuation_outfile)
        #         pypdftk.concat([outfile, continuation_outfile], md5_directory + json_file_md5 + '_all_pages_temp.pdf')
        #         shutil.copy(md5_directory + json_file_md5 + '_all_pages_temp.pdf', outfile)
        #         additional_page_counter += 1
        #         os.remove(md5_directory + json_file_md5 + '_all_pages_temp.pdf')
        #
        # # Add the F99 attachment
        # if 'attachment_file' in request.files:
        #     pypdftk.concat([outfile, md5_directory + 'attachment.pdf'], md5_directory + 'all_pages.pdf')
        #     os.remove(md5_directory + 'attachment.pdf')
        # else:
        #     shutil.copy(outfile, md5_directory + 'all_pages.pdf')
        # os.remove(md5_directory + json_file_md5 +'_temp.pdf')
        # push output file to AWS
        s3 = boto3.client('s3')
        s3.upload_file(md5_directory + 'all_pages.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                       md5_directory+'all_pages.pdf',ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
        response = {
            # 'file_name': '{}.pdf'.format(json_file_md5),
            'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5)+'all_pages.pdf'
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

