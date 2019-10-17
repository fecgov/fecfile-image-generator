import flask
import boto3
import re
import os
import os.path
import pypdftk
import shutil

from os import path
from flask import json
from flask import request, current_app
from flask_api import status
from routes.src import tmoflask, utils, common, form
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject


# return the list of files in a directory
def directory_files(directory):
    files_list = []
    file_names = sorted(os.listdir(directory))
    for file_name in file_names:
        files_list.append(directory + file_name)
    return files_list


# merge two dictionaries and return
def merge(dict1, dict2):
    res = {**dict1, **dict2}
    return res


# Error handling
def error(msg):
    if flask.request.method == "POST":
        envelope = common.get_return_envelope(
            'false', msg
        )
        status_code = status.HTTP_400_BAD_REQUEST
        return flask.jsonify(**envelope), status_code


# stamp_print is a flag that will be passed at the time of submitting a report.
def print_pdftk(stamp_print):
    # check if json_file is in the request
    try:
        if 'json_file' in request.files:
            total_no_of_pages = 0
            page_no = 1
            has_sa_schedules = has_sb_schedules = False
            json_file = request.files.get('json_file')

            # generate md5 for json file
            # FIXME: check if PDF already exist with md5, if exist return pdf instead of re-generating PDF file.
            json_file_md5 = utils.md5_for_file(json_file)
            json_file.stream.seek(0)

            md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
            os.makedirs(md5_directory, exist_ok=True)
            infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F3X')
            # save json file as md5 file name
            json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
            outfile = md5_directory + json_file_md5 + '_temp.pdf'
            # load json file
            f3x_json = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
            # setting timestamp and imgno to empty as these needs to show up after submission
            if stamp_print != 'stamp':
                f3x_json['FILING_TIMESTAMP'] = ''
                f3x_json['IMGNO'] = ''

            # read data from json file
            f3x_data = f3x_json['data']

            # check if summary is present in fecDataFile
            f3x_summary = []
            if 'summary' in f3x_data:
                f3x_summary_temp = f3x_data['summary']
                f3x_summary = {'cashOnHandYear': f3x_summary_temp['cashOnHandYear']}
                # building colA_ and colB_ mapping data for PDF
                f3x_col_a = f3x_summary_temp['colA']
                f3x_col_b = f3x_summary_temp['colB']
                for key in f3x_col_a:
                    f3x_summary['colA_' + key] = '{0:.2f}'.format(f3x_col_a[key])
                for key in f3x_col_b:
                    f3x_summary['colB_' + key] = '{0:.2f}'.format(f3x_col_b[key])

            # split coverage start date and coverage end date to set month, day, and year
            coverage_start_date_array = f3x_data['coverageStartDate'].split("/")
            f3x_data['coverageStartDateMonth'] = coverage_start_date_array[0]
            f3x_data['coverageStartDateDay'] = coverage_start_date_array[1]
            f3x_data['coverageStartDateYear'] = coverage_start_date_array[2]

            coverage_end_date_array = f3x_data['coverageEndDate'].split("/")
            f3x_data['coverageEndDateMonth'] = coverage_end_date_array[0]
            f3x_data['coverageEndDateDay'] = coverage_end_date_array[1]
            f3x_data['coverageEndDateYear'] = coverage_end_date_array[2]

            # checking for signed date, it is only available for submitted reports
            if len(f3x_data['dateSigned']) > 0:
                date_signed_array = f3x_data['dateSigned'].split("/")
                f3x_data['dateSignedMonth'] = date_signed_array[0]
                f3x_data['dateSignedDay'] = date_signed_array[1]
                f3x_data['dateSignedYear'] = date_signed_array[2]

            # build treasurer name to map it to PDF template
            treasurer_full_name = []
            treasurer_full_name.append(f3x_data['treasurerLastName'])
            treasurer_full_name.append(f3x_data['treasurerFirstName'])
            treasurer_full_name.append(f3x_data['treasurerMiddleName'])
            treasurer_full_name.append(f3x_data['treasurerPrefix'])
            treasurer_full_name.append(f3x_data['treasurerSuffix'])
            f3x_data['treasurerFullName'] = ",".join(map(str, treasurer_full_name))
            f3x_data['treasurerName'] = f3x_data['treasurerLastName'] + "," + f3x_data['treasurerFirstName']
            f3x_data['efStamp'] = '[Electronically Filed]'

            # checking if json contains summary details, for individual transactions print there wouldn't be summary
            if len(f3x_summary) > 0:
                total_no_of_pages = 5
                f3x_data_summary_array = [f3x_data, f3x_summary]
            else:
                f3x_data_summary_array = [f3x_data]
            f3x_data_summary = {i: j for x in f3x_data_summary_array for i, j in x.items()}

            # process all schedules and build the PDF's
            process_output, total_no_of_pages = process_schedules(f3x_data, md5_directory,total_no_of_pages)

            has_sa_schedules = process_output.get('has_sa_schedules')
            has_sb_schedules = process_output.get('has_sb_schedules')
            has_sc_schedules = process_output.get('has_sc_schedules')

            if len(f3x_summary) > 0:
                f3x_data_summary['PAGESTR'] = "PAGE " + str(page_no) + " / " + str(total_no_of_pages)
                pypdftk.fill_form(infile, f3x_data_summary, outfile)
                shutil.copy(outfile, md5_directory + 'F3X_Summary.pdf')
                os.remove(md5_directory + json_file_md5 + '_temp.pdf')

                # checking for sa transactions
                if has_sa_schedules:
                    pypdftk.concat([md5_directory + 'F3X_Summary.pdf', md5_directory + 'SA/all_pages.pdf'], md5_directory + 'all_pages.pdf')
                    os.remove(md5_directory + 'SA/all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SA')
                else:
                    shutil.copy(md5_directory + 'F3X_Summary.pdf', md5_directory + 'all_pages.pdf')

                # checking for sb transactions
                if has_sb_schedules:
                    pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SB/all_pages.pdf'], md5_directory + 'temp_all_pages.pdf')
                    shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                    os.remove(md5_directory + 'SB/all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SB')

                # checking for sc transactions
                if has_sc_schedules:
                    pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SC/all_pages.pdf'], md5_directory + 'temp_all_pages.pdf')
                    shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                    os.remove(md5_directory + 'SC/all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SC')

                # if not (has_sa_schedules or has_sb_schedules or has_sc_schedules):
                #     shutil.move(md5_directory + 'F3X_Summary.pdf', md5_directory + 'all_pages.pdf')
            else:
                # no summary, expecting it to be from individual transactions
                if has_sa_schedules:
                    shutil.move(md5_directory + 'SA/all_pages.pdf', md5_directory + 'all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SA')

                if has_sb_schedules:
                    if path.exists(md5_directory + 'all_pages.pdf'):
                        pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SB/all_pages.pdf'], md5_directory + 'temp_all_pages.pdf')
                        shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                    else:
                        shutil.move(md5_directory + 'SB/all_pages.pdf', md5_directory + 'all_pages.pdf')
                    os.remove(md5_directory + 'SB/all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SB')

                if has_sc_schedules:
                    if path.exists(md5_directory + 'all_pages.pdf'):
                        pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SC/all_pages.pdf'], md5_directory + 'temp_all_pages.pdf')
                        shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                    else:
                        shutil.move(md5_directory + 'SC/all_pages.pdf', md5_directory + 'all_pages.pdf')
                    os.remove(md5_directory + 'SC/all_pages.pdf')
                    shutil.rmtree(md5_directory + 'SC')

            # push output file to AWS
            s3 = boto3.client('s3')
            s3.upload_file(md5_directory + 'all_pages.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                           md5_directory + 'all_pages.pdf',
                           ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
            response = {
                # 'file_name': '{}.pdf'.format(json_file_md5),
                'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5) + 'all_pages.pdf'
            }

            # return response
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
    except Exception as e:
        return error('Error generating print preview, error message: ' + str(e))


def process_schedules(f3x_data, md5_directory, total_no_of_pages):
    # Calculate total number of pages for schedules
    sb_line_numbers = ['21B', '22', '23', '26', '27', '28A', '28B', '28C', '29', '30B']
    sc_sa_line_numbers = ['13', '14']
    sc_sb_line_numbers = ['26', '27']
    sa_schedules = []
    sb_schedules = []
    has_sc_schedules = has_sa_schedules = has_sb_schedules = False
    sa_schedules_cnt = sb_schedules_cnt = 0
    total_sc_pages = 0

    # check if schedules exist in data file
    if 'schedules' in f3x_data:
        schedules = f3x_data['schedules']

        # Checking SC first as it has SA and SB transactions in it
        if 'SC' in schedules:
            sc_schedules = schedules.get('SC')
            sc_schedules_cnt = len(sc_schedules)
            sc1_schedules_cnt = 0
            additional_sc_pg_cnt = 0
            if sc_schedules_cnt > 0:
                has_sc_schedules = True
                os.makedirs(md5_directory + 'SC', exist_ok=True)
                for sc_count in range(sc_schedules_cnt):
                    if 'child' in sc_schedules[sc_count]:
                        sc_child_schedules = sc_schedules[sc_count]['child']
                        sc_child_schedules_count = len(sc_child_schedules)
                        sc2_schedules_cnt = 0
                        for sc_child_count in range(sc_child_schedules_count):
                            if sc_schedules[sc_count].get('child')[sc_child_count].get('lineNumber') in sc_sa_line_numbers:
                                if 'SA' not in schedules:
                                    schedules['SA'] = []
                                schedules['SA'].append(sc_schedules[sc_count]['child'][sc_child_count])
                            elif sc_schedules[sc_count]['child'][sc_child_count]['lineNumber'] in sc_sb_line_numbers:
                                if 'SB' not in schedules:
                                    schedules['SB'] = []
                                schedules['SB'].append(sc_schedules[sc_count]['child'][sc_child_count])
                            elif sc_schedules[sc_count]['child'][sc_child_count]['transactionTypeIdentifier'] in ['SC1']:
                                sc1_schedules_cnt += 1
                            elif sc_schedules[sc_count]['child'][sc_child_count]['transactionTypeIdentifier'] in ['SC2']:
                                sc2_schedules_cnt += 1
                        if sc2_schedules_cnt > 4:
                            additional_sc_pg_cnt += int(sc2_schedules_cnt/4)
            total_sc_pages = sc_schedules_cnt + sc1_schedules_cnt + additional_sc_pg_cnt

        if 'SA' in schedules:
            sa_start_page = total_no_of_pages
            sa_schedules.extend(schedules.get('SA'))
            sa_schedules_cnt = len(sa_schedules)

            # if sa_schedules_cnt > 0:
            if sa_schedules:
                has_sa_schedules = True
                os.makedirs(md5_directory + 'SA', exist_ok=True)
                # building array for all SA line numbers
                sa_11a = []
                sa_11b = []
                sa_11c = []
                sa_12 = []
                sa_13 = []
                sa_14 = []
                sa_15 = []
                sa_16 = []
                sa_17 = []

                sa_11a_last_page_cnt = sa_11b_last_page_cnt = sa_11c_last_page_cnt = sa_12_last_page_cnt = 3
                sa_13_last_page_cnt = sa_14_last_page_cnt = sa_15_last_page_cnt = sa_16_last_page_cnt = 3
                sa_17_last_page_cnt = 3

                sa_11a_page_cnt = sa_11b_page_cnt = sa_11c_page_cnt = sa_12_page_cnt = 0
                sa_13_page_cnt = sa_14_page_cnt = sa_15_page_cnt = sa_16_page_cnt = 0
                sa_17_page_cnt = 0

                # process for each Schedule A
                for sa_count in range(sa_schedules_cnt):
                    process_sa_line_numbers(sa_11a, sa_11b, sa_11c, sa_12, sa_13, sa_14, sa_15, sa_16, sa_17,
                                            sa_schedules[sa_count])

                    if 'child' in sa_schedules[sa_count]:
                        sa_child_schedules = sa_schedules[sa_count]['child']

                        sa_child_schedules_count = len(sa_child_schedules)
                        for sa_child_count in range(sa_child_schedules_count):
                            if sa_schedules[sa_count]['child'][sa_child_count]['lineNumber'] in sb_line_numbers:
                                sb_schedules.append(sa_schedules[sa_count]['child'][sa_child_count])
                            else:
                                process_sa_line_numbers(sa_11a, sa_11b, sa_11c, sa_12, sa_13, sa_14, sa_15, sa_16,
                                                        sa_17,
                                                        sa_schedules[sa_count]['child'][sa_child_count])
                # calculate number of pages for SA line numbers
                sa_11a_page_cnt, sa_11a_last_page_cnt = calculate_page_count(sa_11a)
                sa_11b_page_cnt, sa_11b_last_page_cnt = calculate_page_count(sa_11b)
                sa_11c_page_cnt, sa_11c_last_page_cnt = calculate_page_count(sa_11c)
                sa_12_page_cnt, sa_12_last_page_cnt = calculate_page_count(sa_12)
                sa_13_page_cnt, sa_13_last_page_cnt = calculate_page_count(sa_13)
                sa_14_page_cnt, sa_14_last_page_cnt = calculate_page_count(sa_14)
                sa_15_page_cnt, sa_15_last_page_cnt = calculate_page_count(sa_15)
                sa_16_page_cnt, sa_16_last_page_cnt = calculate_page_count(sa_16)
                sa_17_page_cnt, sa_17_last_page_cnt = calculate_page_count(sa_17)

                # calculate total number of pages
                total_no_of_pages = (total_no_of_pages + sa_11a_page_cnt + sa_11b_page_cnt + sa_11c_page_cnt
                                     + sa_12_page_cnt + sa_13_page_cnt + sa_14_page_cnt + sa_15_page_cnt
                                     + sa_16_page_cnt + sa_17_page_cnt)

                sb_start_page = total_no_of_pages

        # checking for SB transactions
        if 'SB' in schedules or len(sb_schedules) > 0:
            sb_start_page = total_no_of_pages
            if 'SB' in schedules:
                sb_schedules.extend(schedules['SB'])
            sb_schedules_cnt = len(sb_schedules)
            if sb_schedules_cnt > 0:
                has_sb_schedules = True
                os.makedirs(md5_directory + 'SB', exist_ok=True)
                # building array for all SB line numbers
                sb_21b = []
                sb_22 = []
                sb_23 = []
                sb_26 = []
                sb_27 = []
                sb_28a = []
                sb_28b = []
                sb_28c = []
                sb_29 = []
                sb_30b = []

                sb_21b_last_page_cnt = sb_22_last_page_cnt = sb_23_last_page_cnt = sb_26_last_page_cnt = 3
                sb_27_last_page_cnt = sb_28a_last_page_cnt = sb_28b_last_page_cnt = sb_28c_last_page_cnt = 3
                sb_29_last_page_cnt = sb_30b_last_page_cnt = 3

                sb_21b_page_cnt = sb_22_page_cnt = sb_23_page_cnt = sb_26_page_cnt = 0
                sb_27_page_cnt = sb_28a_page_cnt = sb_28b_page_cnt = sb_28c_page_cnt = 0
                sb_29_page_cnt = sb_30b_page_cnt = 0

                # process for each Schedule B
                for sb_count in range(sb_schedules_cnt):
                    process_sb_line_numbers(sb_21b, sb_22, sb_23, sb_26, sb_27, sb_28a, sb_28b, sb_28c, sb_29,
                                            sb_30b, sb_schedules[sb_count])

                    if 'child' in sb_schedules[sb_count]:
                        sb_child_schedules = sb_schedules[sb_count]['child']

                        sb_child_schedules_count = len(sb_child_schedules)
                        for sb_child_count in range(sb_child_schedules_count):
                            if sb_schedules[sb_count]['child'][sb_child_count]['lineNumber'] in sb_line_numbers:
                                process_sb_line_numbers(sb_21b, sb_22, sb_23, sb_26, sb_27, sb_28a, sb_28b, sb_28c,
                                                        sb_29, sb_30b, sb_schedules[sb_count]['child'][sb_child_count])

                sb_21b_page_cnt, sb_21b_last_page_cnt = calculate_page_count(sb_21b)
                sb_22_page_cnt, sb_22_last_page_cnt = calculate_page_count(sb_22)
                sb_23_page_cnt, sb_23_last_page_cnt = calculate_page_count(sb_23)
                sb_26_page_cnt, sb_26_last_page_cnt = calculate_page_count(sb_26)
                sb_27_page_cnt, sb_27_last_page_cnt = calculate_page_count(sb_27)
                sb_28a_page_cnt, sb_28a_last_page_cnt = calculate_page_count(sb_28a)
                sb_28b_page_cnt, sb_28b_last_page_cnt = calculate_page_count(sb_28b)
                sb_28c_page_cnt, sb_28c_last_page_cnt = calculate_page_count(sb_28c)
                sb_29_page_cnt, sb_29_last_page_cnt = calculate_page_count(sb_29)
                sb_30b_page_cnt, sb_30b_last_page_cnt = calculate_page_count(sb_30b)

                total_no_of_pages = (total_no_of_pages + sb_21b_page_cnt + sb_22_page_cnt + sb_23_page_cnt
                                     + sb_26_page_cnt + sb_27_page_cnt + sb_28a_page_cnt + sb_28b_page_cnt
                                     + sb_28c_page_cnt + sb_29_page_cnt + sb_30b_page_cnt)

        sc_start_page = total_no_of_pages + 1
        total_no_of_pages += total_sc_pages
        # Schedule A line number processing starts here
        if sa_schedules_cnt > 0:
            # process Schedule 11AI
            sa_11a_start_page = sa_start_page
            process_sa_line(f3x_data, md5_directory, '11AI', sa_11a, sa_11a_page_cnt, sa_11a_start_page,
                            sa_11a_last_page_cnt, total_no_of_pages)

            # process Schedule 11B
            sa_11b_start_page = sa_11a_start_page + sa_11a_page_cnt
            process_sa_line(f3x_data, md5_directory, '11B', sa_11b, sa_11b_page_cnt, sa_11b_start_page,
                            sa_11b_last_page_cnt, total_no_of_pages)

            # process Schedule 11C
            sa_11c_start_page = sa_11b_start_page + sa_11b_page_cnt
            process_sa_line(f3x_data, md5_directory, '11C', sa_11c, sa_11c_page_cnt, sa_11c_start_page,
                            sa_11c_last_page_cnt, total_no_of_pages)

            # process Schedule 12
            sa_12_start_page = sa_11c_start_page + sa_11c_page_cnt
            process_sa_line(f3x_data, md5_directory, '12', sa_12, sa_12_page_cnt, sa_12_start_page,
                            sa_12_last_page_cnt, total_no_of_pages)

            # process Schedule 13
            sa_13_start_page = sa_12_start_page + sa_12_page_cnt
            process_sa_line(f3x_data, md5_directory, '13', sa_13, sa_13_page_cnt, sa_13_start_page,
                            sa_13_last_page_cnt, total_no_of_pages)

            # process Schedule 14
            sa_14_start_page = sa_13_start_page + sa_13_page_cnt
            process_sa_line(f3x_data, md5_directory, '14', sa_14, sa_14_page_cnt, sa_14_start_page,
                            sa_14_last_page_cnt, total_no_of_pages)

            # process Schedule 15
            sa_15_start_page = sa_14_start_page + sa_14_page_cnt
            process_sa_line(f3x_data, md5_directory, '15', sa_15, sa_15_page_cnt, sa_15_start_page,
                            sa_15_last_page_cnt, total_no_of_pages)

            # process Schedule 16
            sa_16_start_page = sa_15_start_page + sa_15_page_cnt
            process_sa_line(f3x_data, md5_directory, '16', sa_16, sa_16_page_cnt, sa_16_start_page,
                            sa_16_last_page_cnt, total_no_of_pages)

            # process Schedule 17
            sa_17_start_page = sa_16_start_page + sa_16_page_cnt
            process_sa_line(f3x_data, md5_directory, '17', sa_17, sa_17_page_cnt, sa_17_start_page,
                            sa_17_last_page_cnt, total_no_of_pages)

        # Schedule B line number processing starts here
        if sb_schedules_cnt > 0:
            # process Schedule 21B
            sb_21b_start_page = sb_start_page
            process_sb_line(f3x_data, md5_directory, '21B', sb_21b, sb_21b_page_cnt, sb_21b_start_page,
                            sb_21b_last_page_cnt, total_no_of_pages)

            # process Schedule 22
            sb_22_start_page = sb_21b_start_page + sb_21b_page_cnt
            process_sb_line(f3x_data, md5_directory, '22', sb_22, sb_22_page_cnt, sb_22_start_page,
                            sb_22_last_page_cnt, total_no_of_pages)

            # process Schedule 23
            sb_23_start_page = sb_22_start_page + sb_22_page_cnt
            process_sb_line(f3x_data, md5_directory, '23', sb_23, sb_23_page_cnt, sb_23_start_page,
                            sb_23_last_page_cnt, total_no_of_pages)

            # process Schedule 26
            sb_26_start_page = sb_23_start_page + sb_23_page_cnt
            process_sb_line(f3x_data, md5_directory, '26', sb_26, sb_26_page_cnt, sb_26_start_page,
                            sb_26_last_page_cnt, total_no_of_pages)

            # process Schedule 27
            sb_27_start_page = sb_26_start_page + sb_26_page_cnt
            process_sb_line(f3x_data, md5_directory, '27', sb_27, sb_27_page_cnt, sb_27_start_page,
                            sb_27_last_page_cnt, total_no_of_pages)

            # process Schedule 28A
            sb_28a_start_page = sb_27_start_page + sb_27_page_cnt
            process_sb_line(f3x_data, md5_directory, '28A', sb_28a, sb_28a_page_cnt, sb_28a_start_page,
                            sb_28a_last_page_cnt, total_no_of_pages)

            # process Schedule 28B
            sb_28b_start_page = sb_28a_start_page + sb_28a_page_cnt
            process_sb_line(f3x_data, md5_directory, '28B', sb_28b, sb_28b_page_cnt, sb_28b_start_page,
                            sb_28b_last_page_cnt, total_no_of_pages)

            # process Schedule 28C
            sb_28c_start_page = sb_28b_start_page + sb_28b_page_cnt
            process_sb_line(f3x_data, md5_directory, '28C', sb_28c, sb_28c_page_cnt, sb_28c_start_page,
                            sb_28c_last_page_cnt, total_no_of_pages)

            # process Schedule 29
            sb_29_start_page = sb_28c_start_page + sb_28c_page_cnt
            process_sb_line(f3x_data, md5_directory, '29', sb_29, sb_29_page_cnt, sb_29_start_page,
                            sb_29_last_page_cnt, total_no_of_pages)

            # process Schedule 30B
            sb_30b_start_page = sb_29_start_page + sb_29_page_cnt
            process_sb_line(f3x_data, md5_directory, '30B', sb_30b, sb_30b_page_cnt, sb_30b_start_page,
                            sb_30b_last_page_cnt, total_no_of_pages)

        if 'SC' in schedules and sc_schedules_cnt > 0:
            sc1_list, sc1_start_page = process_sc_line(f3x_data, md5_directory, sc_schedules, sc_start_page, total_no_of_pages)
        else:
            sc1_list = []

        if sc1_list:
            for sc1 in sc1_list:
                process_sc1_line(f3x_data, md5_directory, sc1, sc1_start_page, total_no_of_pages)
                sc1_start_page += 1

        output_data = {
                        'has_sa_schedules': has_sa_schedules,
                        'has_sb_schedules': has_sb_schedules,
                        'has_sc_schedules': has_sc_schedules
                        }
        return output_data, total_no_of_pages

def process_sc_line(f3x_data, md5_directory, sc_schedules, sc_start_page, total_no_of_pages):
    sc_schedule_total = 0.00
    os.makedirs(md5_directory + 'SC/', exist_ok=True)
    sc_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SC')
    sc1_list = []
    for sc in sc_schedules:
        page_subtotal = '{0:.2f}'.format(float(sc.get('loanBalance')))
        sc_schedule_total += float(page_subtotal)
        sc_schedule_page_dict = {}
        sc_schedule_page_dict['TRANSACTION_ID'] = sc.get('transactionId')
        sc_schedule_page_dict['totalPages'] = total_no_of_pages
        sc_schedule_page_dict['committeeName'] = f3x_data.get('committeeName')
        sc_schedule_page_dict['pageSubtotal'] = page_subtotal
        for i in ['memoCode', 'memoDescription', 'lenderStreet1', 'lenderStreet2', 'lenderCity', 'lenderState', 'lenderZipCode', 'electionOtherDescription', 'isLoanSecured']:
            sc_schedule_page_dict[i] = sc.get(i)
        for i in ['loanAmountOriginal','loanPaymentToDate', 'loanBalance', 'loanInterestRate']:
            sc_schedule_page_dict[i] =  '{0:.2f}'.format(float(sc.get(i)))
        if 'electionCode' in sc and sc.get('electionCode') != "":
            sc_schedule_page_dict['electionType'] = sc.get('electionCode')[0:1]
            sc_schedule_page_dict['electionYear'] = sc.get('electionCode')[1:5]
        lenderName =""
        if sc.get('lenderOrganizationName') == "":
            for i in ['lenderPrefix', 'lenderLastName', 'lenderFirstName', 'lenderMiddleName', 'lenderSuffix']:
                if sc.get(i) != "":
                    lenderName += sc.get(i) + " "
            sc_schedule_page_dict['lenderName'] = lenderName [0:-1]
        else:
            sc_schedule_page_dict['lenderName'] = sc.get('lenderOrganizationName')
        if 'loanIncurredDate' in sc:
            date_array = sc.get('loanIncurredDate').split("/")
            sc_schedule_page_dict['loanIncurredDateMonth'] = date_array[0]
            sc_schedule_page_dict['loanIncurredDateDay'] = date_array[1]
            sc_schedule_page_dict['loanIncurredDateYear'] = date_array[2]
        if 'loanDueDate' in sc:
            if "-" in sc.get('loanDueDate'):
                date_array = sc.get('loanDueDate').split("-")
                sc_schedule_page_dict['loanDueDateMonth'] = date_array[1]
                sc_schedule_page_dict['loanDueDateDay'] = date_array[2]
                sc_schedule_page_dict['loanDueDateYear'] = date_array[0]
            else:
                date_array = sc.get('loanDueDate').split("/")
                sc_schedule_page_dict['loanDueDateMonth'] = date_array[0]
                sc_schedule_page_dict['loanDueDateDay'] = date_array[1]
                sc_schedule_page_dict['loanDueDateYear'] = date_array[2]
        if 'child' in sc and sc.get('child'):
            sc2 = []
            for sc_child in sc.get('child'):
                if sc_child.get('transactionTypeIdentifier') == 'SC2':
                    sc2.append(sc_child)
                elif sc_child.get('transactionTypeIdentifier') == 'SC1':
                    sc_child['SCPageNo'] = sc_start_page
                    sc1_list.append(sc_child)
            if sc2:
                sc2_list_list = []
                temp_sc2 = []
                for i in range(len(sc2)):
                    temp_sc2.append(sc2[i])
                    if i%4 == 3 or i == len(sc2)-1:
                        sc2_list_list.append(temp_sc2)
                        temp_sc2 = []
                for i in range(len(sc2_list_list)):
                    sc_schedule_single_page_dict = {}
                    sc_schedule_single_page_dict = sc_schedule_page_dict
                    for j in range(len(sc2_list_list[i])):
                        sc2_name = ""
                        for k in ['preffix', 'lastName', 'firstName', 'middleName', 'suffix']:
                            if sc2_list_list[i][j].get(k) != "":
                                sc2_name += sc2_list_list[i][j].get(k) + " "
                        sc_schedule_single_page_dict['name{}'.format(j+1)] = sc2_name[0:-1]
                        sc_schedule_single_page_dict['street1_{}'.format(j+1)] = sc2_list_list[i][j].get('street1')
                        sc_schedule_single_page_dict['street2_{}'.format(j+1)] = sc2_list_list[i][j].get('street2')
                        sc_schedule_single_page_dict['city_{}'.format(j+1)] = sc2_list_list[i][j].get('city')
                        sc_schedule_single_page_dict['state_{}'.format(j+1)] = sc2_list_list[i][j].get('state')
                        sc_schedule_single_page_dict['zipCode_{}'.format(j+1)] = sc2_list_list[i][j].get('zipCode')
                        sc_schedule_single_page_dict['employer_{}'.format(j+1)] = sc2_list_list[i][j].get('employer')
                        sc_schedule_single_page_dict['occupation_{}'.format(j+1)] = sc2_list_list[i][j].get('occupation')
                        sc_schedule_single_page_dict['guaranteedAmount_{}'.format(j+1)] = '{0:.2f}'.format(float(sc2_list_list[i][j].get('guaranteedAmount')))
                    sc_schedule_single_page_dict['pageNo'] = sc_start_page
                    if sc_schedules[len(sc_schedules)-1].get('transactionId') == sc_schedule_single_page_dict.get('TRANSACTION_ID') and i == len(sc2_list_list)-1:
                        sc_schedule_single_page_dict['scheduleTotal'] = '{0:.2f}'.format(sc_schedule_total)
                    sc_outfile = md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'
                    pypdftk.fill_form(sc_infile, sc_schedule_single_page_dict, sc_outfile)
                    for j in range(len(sc2_list_list[i])):
                        del sc_schedule_single_page_dict['name{}'.format(j+1)]
                        del sc_schedule_single_page_dict['street1_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['street2_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['city_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['state_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['zipCode_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['employer_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['occupation_{}'.format(j+1)]
                        del sc_schedule_single_page_dict['guaranteedAmount_{}'.format(j+1)]
                    if path.isfile(md5_directory + 'SC/all_pages.pdf'):
                        pypdftk.concat([md5_directory + 'SC/all_pages.pdf', md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'],
                                       md5_directory + 'SC/temp_all_pages.pdf')
                        os.rename(md5_directory + 'SC/temp_all_pages.pdf', md5_directory + 'SC/all_pages.pdf')
                    else:
                        os.rename(md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf', md5_directory + 'SC/all_pages.pdf')
                    sc_start_page += 1
            else:
                sc_schedule_page_dict['pageNo'] = sc_start_page
                if sc_schedules[len(sc_schedules)-1].get('transactionId') == sc_schedule_page_dict.get('TRANSACTION_ID'):
                    sc_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(sc_schedule_total)
                sc_outfile = md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'
                pypdftk.fill_form(sc_infile, sc_schedule_page_dict, sc_outfile)
                if path.isfile(md5_directory + 'SC/all_pages.pdf'):
                    pypdftk.concat([md5_directory + 'SC/all_pages.pdf', md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'],
                                   md5_directory + 'SC/temp_all_pages.pdf')
                    os.rename(md5_directory + 'SC/temp_all_pages.pdf', md5_directory + 'SC/all_pages.pdf')
                else:
                    os.rename(md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf', md5_directory + 'SC/all_pages.pdf')
                sc_start_page += 1
        else:
            sc_schedule_page_dict['pageNo'] = sc_start_page
            if sc_schedules[len(sc_schedules)-1].get('transactionId') == sc_schedule_page_dict.get('TRANSACTION_ID'):
                sc_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(sc_schedule_total)
            sc_outfile = md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'
            pypdftk.fill_form(sc_infile, sc_schedule_page_dict, sc_outfile)
            if path.isfile(md5_directory + 'SC/all_pages.pdf'):
                pypdftk.concat([md5_directory + 'SC/all_pages.pdf', md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf'],
                               md5_directory + 'SC/temp_all_pages.pdf')
                os.rename(md5_directory + 'SC/temp_all_pages.pdf', md5_directory + 'SC/all_pages.pdf')
            else:
                os.rename(md5_directory + 'SC' + '/page_' + str(sc_start_page) + '.pdf', md5_directory + 'SC/all_pages.pdf')
            sc_start_page += 1
    return sc1_list, sc_start_page

def process_sc1_line(f3x_data, md5_directory, sc1, sc1_start_page, total_no_of_pages):
    sc1_schedule_page_dict = {}
    sc1_schedule_page_dict['PAGENO'] = sc1_start_page
    sc1_schedule_page_dict['TRANSACTION_ID'] = sc1.get('transactionId')
    sc1_schedule_page_dict['TOTALPAGES'] = total_no_of_pages
    sc1_schedule_page_dict['committeeName'] = f3x_data.get('committeeName')
    sc1_schedule_page_dict['committeeId'] = f3x_data.get('committeeId')
    sc1_schedule_page_dict['lenderName'] = sc1.get('lenderOrganizationName')
    for i in ['lenderStreet1', 'lenderStreet2', 'lenderCity', 'lenderState', 'lenderZipCode', 'loanInterestRate', 'isLoanRestructured', 'otherPartiesLiable',
                    'pledgedCollateralIndicator', 'pledgeCollateralDescription', 'perfectedInterestIndicator', 'futureIncomeIndicator', 'SCPageNo']:
        sc1_schedule_page_dict[i] = sc1.get(i)
    if sc1.get('loanIncurredDate') != "":
        date_array = sc1.get('loanIncurredDate').split("/")
        sc1_schedule_page_dict['loanIncurredDateMonth'] = date_array[0]
        sc1_schedule_page_dict['loanIncurredDateDay'] = date_array[1]
        sc1_schedule_page_dict['loanIncurredDateYear'] = date_array[2]
    if sc1.get('loanDueDate') != "":
        date_array = sc1.get('loanDueDate').split("/")
        sc1_schedule_page_dict['loanDueDateMonth'] = date_array[0]
        sc1_schedule_page_dict['loanDueDateDay'] = date_array[1]
        sc1_schedule_page_dict['loanDueDateYear'] = date_array[2]
    if sc1.get('originalLoanDate') != "":
        date_array = sc1.get('originalLoanDate').split("/")
        sc1_schedule_page_dict['originalLoanDateMonth'] = date_array[0]
        sc1_schedule_page_dict['originalLoanDateDay'] = date_array[1]
        sc1_schedule_page_dict['originalLoanDateYear'] = date_array[2]
    if sc1.get('depositoryAccountEstablishedDate') != "":
        date_array = sc1.get('depositoryAccountEstablishedDate').split("/")
        sc1_schedule_page_dict['ACCOUNT_EST_DATE_MM'] = date_array[0]
        sc1_schedule_page_dict['ACCOUNT_EST_DATE_DD'] = date_array[1]
        sc1_schedule_page_dict['ACCOUNT_EST_DATE_YY'] = date_array[2]
    sc1_schedule_page_dict['loanAmount'] = '{0:.2f}'.format(float(sc1.get('loanAmount')))
    sc1_schedule_page_dict['creditAmountThisDraw'] = '{0:.2f}'.format(float(sc1.get('creditAmountThisDraw')))
    sc1_schedule_page_dict['totalOutstandingBalance'] = '{0:.2f}'.format(float(sc1.get('totalOutstandingBalance')))
    sc1_schedule_page_dict['BACK_REF_TRAN_ID'] = sc1.get('backReferenceTransactionIdNumber')
    sc1_schedule_page_dict['pledgeCollateralAmount'] = '{0:.2f}'.format(float(sc1.get('pledgeCollateralAmount')))
    sc1_schedule_page_dict['PLEDGE_DESC'] = sc1.get('futureIncomeDescription')
    sc1_schedule_page_dict['PLEDGE_ESTIMATED_AMOUNT'] = '{0:.2f}'.format(float(sc1.get('futureIncomeEstimate')))
    treasurerName = ""
    for i in ['treasurerPrefix', 'treasurerLastName', 'treasurerFirstName', 'treasurerMiddleName', 'treasurerSuffix']:
        if sc1.get(i) != "":
            treasurerName += sc1.get(i) + " "
    sc1_schedule_page_dict['COMMITTEE_TREASURER_NAME'] = treasurerName[0:-1]
    sc1_schedule_page_dict['DEPOSITORY_NAME'] = sc1.get('depositoryAccountLocation')
    sc1_schedule_page_dict['DEPOSITORY_STREET1'] = sc1.get('depositoryAccountStreet1')
    sc1_schedule_page_dict['DEPOSITORY_STREET2'] = sc1.get('depositoryAccountStreet2')
    sc1_schedule_page_dict['DEPOSITORY_CITY'] = sc1.get('depositoryAccountCity')
    sc1_schedule_page_dict['DEPOSITORY_STATE'] = sc1.get('depositoryAccountState')
    sc1_schedule_page_dict['DEPOSITORY_ZIP'] = sc1.get('depositoryAccountZipCode')
    sc1_schedule_page_dict['BASIS'] = sc1.get('basisOfLoanDescription')
    if sc1.get('treasurerSignedDate') != "":
        date_array = sc1.get('treasurerSignedDate').split("/")
        sc1_schedule_page_dict['TREASUER_SIGN_DATE_MM'] = date_array[0]
        sc1_schedule_page_dict['TREASUER_SIGN_DATE_DD'] = date_array[1]
        sc1_schedule_page_dict['TREASUER_SIGN_DATE_YY'] = date_array[2]
    authorizedName = ""
    for i in ['authorizedPrefix', 'authorizedLastName', 'authorizedFirstName', 'authorizedMiddleName', 'authorizedSuffix']:
        if sc1.get(i) != "":
            authorizedName += sc1.get(i) + " "
    sc1_schedule_page_dict['AUTH_REP_NAME'] = authorizedName[0:-1]
    sc1_schedule_page_dict['AUTH_REP_TITLE'] = sc1.get('authorizedTitle')
    if sc1.get('authorizedSignedDate') != "":
        date_array = sc1.get('authorizedSignedDate').split("/")
        sc1_schedule_page_dict['AUTH_REP_SIGN_MM'] = date_array[0]
        sc1_schedule_page_dict['AUTH_REP_SIGN_DD'] = date_array[1]
        sc1_schedule_page_dict['AUTH_REP_SIGN_YY'] = date_array[2]
    sc1_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SC1')
    sc1_outfile = md5_directory + 'SC' + '/page_' + str(sc1_start_page) + '.pdf'
    pypdftk.fill_form(sc1_infile, sc1_schedule_page_dict, sc1_outfile)
    if path.isfile(md5_directory + 'SC/all_pages.pdf'):
        pypdftk.concat([md5_directory + 'SC/all_pages.pdf', md5_directory + 'SC' + '/page_' + str(sc1_start_page) + '.pdf'],
                       md5_directory + 'SC/temp_all_pages.pdf')
        os.rename(md5_directory + 'SC/temp_all_pages.pdf', md5_directory + 'SC/all_pages.pdf')
    else:
        os.rename(md5_directory + 'SC/all_pages.pdf', md5_directory + 'SC' + '/page_' + str(sc1_start_page) + '.pdf')


# This method is invoked for each SA line number, it builds PDF for line numbers
def process_sa_line(f3x_data, md5_directory, line_number, sa_line, sa_line_page_cnt, sa_line_start_page,
                    sa_line_last_page_cnt, total_no_of_pages):
    has_sa_schedules = False
    if len(sa_line) > 0:
        sa_line_start_page += 1
        has_sa_schedules = True
        schedule_total = 0.00
        os.makedirs(md5_directory + 'SA/' + line_number, exist_ok=True)
        sa_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SA')
        if sa_line_page_cnt > 0:
            for sa_page_no in range(sa_line_page_cnt):
                page_subtotal = 0.00
                last_page = False
                sa_schedule_page_dict = {}
                sa_schedule_page_dict['lineNumber'] = line_number
                sa_schedule_page_dict['pageNo'] = sa_line_start_page + sa_page_no
                sa_schedule_page_dict['totalPages'] = total_no_of_pages
                page_start_index = sa_page_no * 3
                if ((sa_page_no + 1) == sa_line_page_cnt):
                    last_page = True
                # This call prepares data to render on PDF
                sa_schedule_dict = build_sa_per_page_schedule_dict(last_page, sa_line_last_page_cnt,
                                                                   page_start_index, sa_schedule_page_dict,
                                                                   sa_line)

                page_subtotal = float(sa_schedule_page_dict['pageSubtotal'])
                schedule_total += page_subtotal
                if sa_line_page_cnt == (sa_page_no + 1):
                    sa_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                sa_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                sa_outfile = md5_directory + 'SA/' + line_number + '/page_' + str(sa_page_no) + '.pdf'
                pypdftk.fill_form(sa_infile, sa_schedule_page_dict, sa_outfile)
        pypdftk.concat(directory_files(md5_directory + 'SA/' + line_number + '/'), md5_directory + 'SA/' + line_number
                       + '/all_pages.pdf')
        # if all_pages.pdf exists in SA folder, concatenate line number pdf to all_pages.pdf
        if path.isfile(md5_directory + 'SA/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SA/all_pages.pdf', md5_directory + 'SA/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SA/temp_all_pages.pdf')
            os.rename(md5_directory + 'SA/temp_all_pages.pdf', md5_directory + 'SA/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SA/' + line_number + '/all_pages.pdf', md5_directory + 'SA/all_pages.pdf')
    return has_sa_schedules


# This method is invoked for each SB line number, it builds PDF for line numbers
def process_sb_line(f3x_data, md5_directory, line_number, sb_line, sb_line_page_cnt, sb_line_start_page,
                    sb_line_last_page_cnt, total_no_of_pages):
    has_sb_schedules = False
    if len(sb_line) > 0:
        schedule_total = 0.00
        os.makedirs(md5_directory + 'SB/' + line_number, exist_ok=True)
        sb_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SB')
        if sb_line_page_cnt > 0:
            sb_line_start_page += 1
            for sb_page_no in range(sb_line_page_cnt):
                page_subtotal = 0.00
                last_page = False
                sb_schedule_page_dict = {}
                sb_schedule_page_dict['lineNumber'] = line_number
                sb_schedule_page_dict['pageNo'] = sb_line_start_page + sb_page_no
                sb_schedule_page_dict['totalPages'] = total_no_of_pages
                page_start_index = sb_page_no * 3
                if ((sb_page_no + 1) == sb_line_page_cnt):
                    last_page = True
                # This call prepares data to render on PDF
                sb_schedule_dict = build_sb_per_page_schedule_dict(last_page, sb_line_last_page_cnt,
                                                                   page_start_index, sb_schedule_page_dict,
                                                                   sb_line)

                page_subtotal = float(sb_schedule_page_dict['pageSubtotal'])
                schedule_total += page_subtotal
                if sb_line_page_cnt == (sb_page_no + 1):
                    sb_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                sb_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                sb_outfile = md5_directory + 'SB/' + line_number + '/page_' + str(sb_page_no) + '.pdf'
                pypdftk.fill_form(sb_infile, sb_schedule_page_dict, sb_outfile)
        pypdftk.concat(directory_files(md5_directory + 'SB/' + line_number + '/'), md5_directory + 'SB/' + line_number
                       + '/all_pages.pdf')
        # if all_pages.pdf exists in SB folder, concatenate line number pdf to all_pages.pdf
        if path.isfile(md5_directory + 'SB/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SB/all_pages.pdf', md5_directory + 'SB/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SB/temp_all_pages.pdf')
            os.rename(md5_directory + 'SB/temp_all_pages.pdf', md5_directory + 'SB/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SB/' + line_number + '/all_pages.pdf', md5_directory + 'SB/all_pages.pdf')
    return has_sb_schedules


# This method calculates number of pages for Schedules
def calculate_page_count(schedules):
    schedules_cnt = len(schedules)
    if int(schedules_cnt % 3) == 0:
        pages_cnt = int(schedules_cnt / 3)
        schedules_in_last_page = 3
    else:
        pages_cnt = int(schedules_cnt / 3) + 1
        schedules_in_last_page = int(schedules_cnt % 3)
    return pages_cnt, schedules_in_last_page


# This method builds line number array for SA
def process_sa_line_numbers(sa_11a, sa_11b, sa_11c, sa_12, sa_13, sa_14, sa_15, sa_16, sa_17, sa_obj):
    if sa_obj['lineNumber'] == '11A' or sa_obj['lineNumber'] == '11AI' or sa_obj['lineNumber'] == '11AII':
        sa_11a.append(sa_obj)
    elif sa_obj['lineNumber'] == '11B':
        sa_11b.append(sa_obj)
    elif sa_obj['lineNumber'] == '11C':
        sa_11c.append(sa_obj)
    elif sa_obj['lineNumber'] == '12':
        sa_12.append(sa_obj)
    elif sa_obj['lineNumber'] == '13':
        sa_13.append(sa_obj)
    elif sa_obj['lineNumber'] == '14':
        sa_14.append(sa_obj)
    elif sa_obj['lineNumber'] == '15':
        sa_15.append(sa_obj)
    elif sa_obj['lineNumber'] == '16':
        sa_16.append(sa_obj)
    elif sa_obj['lineNumber'] == '17':
        sa_17.append(sa_obj)

# This method builds line number array for SB
def process_sb_line_numbers(sb_21b, sb_22, sb_23, sb_26, sb_27, sb_28a, sb_28b, sb_28c, sb_29,
                            sb_30b, sb_obj):
    if sb_obj['lineNumber'] == '21B':
        sb_21b.append(sb_obj)
    elif sb_obj['lineNumber'] == '22':
        sb_22.append(sb_obj)
    elif sb_obj['lineNumber'] == '23':
        sb_23.append(sb_obj)
    elif sb_obj['lineNumber'] == '26':
        sb_26.append(sb_obj)
    elif sb_obj['lineNumber'] == '27':
        sb_27.append(sb_obj)
    elif sb_obj['lineNumber'] == '28A':
        sb_28a.append(sb_obj)
    elif sb_obj['lineNumber'] == '28B':
        sb_28b.append(sb_obj)
    elif sb_obj['lineNumber'] == '28C':
        sb_28c.append(sb_obj)
    elif sb_obj['lineNumber'] == '29':
        sb_29.append(sb_obj)
    elif sb_obj['lineNumber'] == '30B':
        sb_30b.append(sb_obj)


# This method builds data for individual SA page
def build_sa_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, sa_schedule_page_dict,
                                    sa_schedules):
    page_subtotal = 0.00
    if not last_page:
        transactions_in_page = 3

    if transactions_in_page == 1:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
    elif transactions_in_page == 2:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
        index = 2
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 1]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
    elif transactions_in_page == 3:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
        index = 2
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 1]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
        index = 3
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 2]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict,
                                         contributor_name)
    sa_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    return sa_schedule_dict


# This method builds data for individual SB page
def build_sb_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, sb_schedule_page_dict,
                                    sb_schedules):
    page_subtotal = 0.00
    if not last_page:
        transactions_in_page = 3
    if transactions_in_page == 1:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
    elif transactions_in_page == 2:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 1]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
    elif transactions_in_page == 3:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 1]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
        index = 3
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 2]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_" + str(index)] = ",".join(map(str, contributor_name))
    sb_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    return sb_schedule_dict


# This method filters data and message data to render PDF
def build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name):
    try:
        if 'contributorLastName' in sa_schedule_dict:
            sa_schedule_page_dict['contributorName_' + str(index)] = (sa_schedule_dict['contributorLastName'] + ','
                                                                      + sa_schedule_dict['contributorFirstName'] + ','
                                                                      + sa_schedule_dict['contributorMiddleName'] + ','
                                                                      + sa_schedule_dict['contributorPrefix'] + ','
                                                                      + sa_schedule_dict['contributorSuffix'])
            del sa_schedule_dict['contributorLastName']
            del sa_schedule_dict['contributorFirstName']
            del sa_schedule_dict['contributorMiddleName']
            del sa_schedule_dict['contributorPrefix']
            del sa_schedule_dict['contributorSuffix']
        elif 'contributorOrgName' in sa_schedule_dict:
            sa_schedule_page_dict["contributorName_" + str(index)] = sa_schedule_dict['contributorOrgName']
            del sa_schedule_dict['contributorOrgName']

        if 'lineNumber' in sa_schedule_dict:
            sa_schedule_page_dict['lineNumber'] = sa_schedule_dict['lineNumber']
            del sa_schedule_dict['lineNumber']

        if 'contributionDate' in sa_schedule_dict:
            date_array = sa_schedule_dict['contributionDate'].split("/")
            sa_schedule_page_dict['contributionDateMonth_' + str(index)] = date_array[0]
            sa_schedule_page_dict['contributionDateDay_' + str(index)] = date_array[1]
            sa_schedule_page_dict['contributionDateYear_' + str(index)] = date_array[2]
            del sa_schedule_dict['contributionDate']

        if 'contributionAmount' in sa_schedule_dict:
            if sa_schedule_dict['contributionAmount'] == '':
                sa_schedule_dict['contributionAmount'] = 0.0
            sa_schedule_page_dict['contributionAmount_' + str(index)] = '{0:.2f}'.format(
                sa_schedule_dict['contributionAmount'])
            del sa_schedule_dict['contributionAmount']

        if 'contributionAggregate' in sa_schedule_dict:
            if sa_schedule_dict['contributionAggregate'] == '':
                sa_schedule_dict['contributionAggregate'] = 0.0
            sa_schedule_page_dict['contributionAggregate_' + str(index)] = '{0:.2f}'.format(
                sa_schedule_dict['contributionAggregate'])
            del sa_schedule_dict['contributionAggregate']

        for key in sa_schedule_dict:
            sa_schedule_page_dict[key + '_' + str(index)] = sa_schedule_dict[key]
    except Exception as e:
        print('Error at key: ' + key + ' in Schedule A transaction: ' + str(sa_schedule_dict))
        raise e


# This method filters data and message data to render PDF
def build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, payee_name):
    try:
        if not sb_schedule_dict.get(key):
            sb_schedule_dict[key] = ""
        if key == 'payeeLastName':
            payee_name.append(sb_schedule_dict[key])
        elif key == 'payeeFirstName':
            payee_name.append(sb_schedule_dict[key])
        elif key == 'payeeMiddleName':
            payee_name.append(sb_schedule_dict[key])
        elif key == 'payeePrefix':
            payee_name.append(sb_schedule_dict[key])
        elif key == 'payeeSuffix':
            payee_name.append(sb_schedule_dict[key])
        elif key == 'expenditureDate':
            date_array = sb_schedule_dict[key].split("/")
            sb_schedule_page_dict['expenditureDateMonth_' + str(index)] = date_array[0]
            sb_schedule_page_dict['expenditureDateDay_' + str(index)] = date_array[1]
            sb_schedule_page_dict['expenditureDateYear_' + str(index)] = date_array[2]
        else:
            if key == 'expenditureAmount' or key == 'expenditureAggregate':
                sb_schedule_page_dict[key + '_' + str(index)] = '{0:.2f}'.format(sb_schedule_dict[key])
            else:
                sb_schedule_page_dict[key + '_' + str(index)] = sb_schedule_dict[key]
    except Exception as e:
        print('Error at key: ' + key + ' in Schedule B transaction: ' + str(sb_schedule_dict))
        raise e