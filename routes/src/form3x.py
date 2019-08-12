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
        files_list.append(directory+file_name)
    return files_list


# merge two dictionaries and return
def merge(dict1, dict2):
    res = {**dict1, **dict2}
    return res


# stamp_print is a flag that will be passed at the time of submitting a report.
def print_pdftk(stamp_print):
    # check if json_file is in the request
    if 'json_file' in request.files:

        total_no_of_pages = 0
        page_no = 1
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
        # pushing json file to aws for testing
        s3 = boto3.client('s3')
        s3.upload_file(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5), current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                        'print_preview.json')
        outfile = md5_directory+json_file_md5+'_temp.pdf'
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
            f3x_col_a = f3x_summary_temp['colA']
            f3x_col_b = f3x_summary_temp['colB']
            for key in f3x_col_a:
                f3x_summary['colA_' + key] = '{0:.2f}'.format(f3x_col_a[key])
            for key in f3x_col_b:
                f3x_summary['colB_' + key] = '{0:.2f}'.format(f3x_col_b[key])
        coverage_start_date_array = f3x_data['coverageStartDate'].split("/")
        f3x_data['coverageStartDateMonth'] = coverage_start_date_array[0]
        f3x_data['coverageStartDateDay'] = coverage_start_date_array[1]
        f3x_data['coverageStartDateYear'] = coverage_start_date_array[2]

        coverage_end_date_array = f3x_data['coverageEndDate'].split("/")
        f3x_data['coverageEndDateMonth'] = coverage_end_date_array[0]
        f3x_data['coverageEndDateDay'] = coverage_end_date_array[1]
        f3x_data['coverageEndDateYear'] = coverage_end_date_array[2]

        if len(f3x_data['dateSigned']) > 0:
            date_signed_array = f3x_data['dateSigned'].split("/")
            f3x_data['dateSignedMonth'] = date_signed_array[0]
            f3x_data['dateSignedDay'] = date_signed_array[1]
            f3x_data['dateSignedYear'] = date_signed_array[2]

        treasurer_full_name = []
        treasurer_full_name.append(f3x_data['treasurerLastName'])
        treasurer_full_name.append(f3x_data['treasurerFirstName'])
        treasurer_full_name.append(f3x_data['treasurerMiddleName'])
        treasurer_full_name.append(f3x_data['treasurerPrefix'])
        treasurer_full_name.append(f3x_data['treasurerSuffix'])
        f3x_data['treasurerFullName'] = ",".join(map(str, treasurer_full_name))
        f3x_data['treasurerName'] = f3x_data['treasurerLastName'] + "," + f3x_data['treasurerFirstName']
        f3x_data['efStamp'] = '[Electronically Filed]'

        if len(f3x_summary) > 0:
            total_no_of_pages = 5
            f3x_data_summary_array = [f3x_data, f3x_summary]
        else:
            f3x_data_summary_array = [f3x_data]
        f3x_data_summary = {i: j for x in f3x_data_summary_array for i, j in x.items()}

        has_sa_schedules, has_sb_schedules, total_no_of_pages = process_schedules(f3x_data, md5_directory, total_no_of_pages)

        if len(f3x_summary) > 0:
            f3x_data_summary['PAGESTR'] = "PAGE " + str(page_no) + " / " + str(total_no_of_pages)
            pypdftk.fill_form(infile, f3x_data_summary, outfile)
            shutil.copy(outfile, md5_directory + 'F3X.pdf')
            os.remove(md5_directory + json_file_md5 +'_temp.pdf')

            # checking for any sa transactions
            if has_sa_schedules:
                pypdftk.concat([md5_directory + 'F3X.pdf', md5_directory + 'SA/all_pages.pdf'],
                               md5_directory + 'all_pages.pdf')
                os.remove(md5_directory + 'SA/all_pages.pdf')
                shutil.rmtree(md5_directory + 'SA')

            if has_sb_schedules:
                pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SB/all_pages.pdf'],
                               md5_directory + 'temp_all_pages.pdf')
                shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                os.remove(md5_directory + 'SB/all_pages.pdf')
                shutil.rmtree(md5_directory + 'SB')

            if not (has_sa_schedules or has_sb_schedules):
                shutil.move(md5_directory + 'F3X.pdf', md5_directory + 'all_pages.pdf')
        else:
            if has_sa_schedules:
                shutil.move(md5_directory + 'SA/all_pages.pdf', md5_directory + 'all_pages.pdf')
                shutil.rmtree(md5_directory + 'SA')

            if has_sb_schedules:
                if path.exists(md5_directory + 'all_pages.pdf'):
                    pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SB/all_pages.pdf'],
                                   md5_directory + 'temp_all_pages.pdf')
                    shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                else:
                    shutil.move(md5_directory + 'SB/all_pages.pdf', md5_directory + 'all_pages.pdf')
                os.remove(md5_directory + 'SB/all_pages.pdf')
                shutil.rmtree(md5_directory + 'SB')

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


def process_schedules(f3x_data, md5_directory, total_no_of_pages):

    # Calculate total number of pages for schedules
    sa_schedules = []
    sa_schedules_cnt = 0
    sa_pages_cnt = 0
    sa_schedules_in_last_page = 3
    has_sa_schedules = False
    sa_start_page = 0

    sb_schedules = []
    sb_schedules_cnt = 0
    sb_pages_cnt = 0
    sb_schedules_in_last_page = 3
    has_sb_schedules = False
    sb_start_page = 0

    # schedule_start_page = total_no_of_pages + 1

    # check if schedules exist in data file
    if 'schedules' in f3x_data:
        schedules = f3x_data['schedules']
        if 'SA' in schedules:
            sa_start_page = total_no_of_pages + 1
            sa_schedules = schedules['SA']
            sa_schedules_cnt = len(sa_schedules)
            if sa_schedules_cnt > 0:
                for sa_count in range(sa_schedules_cnt):
                    if 'child' in sa_schedules[sa_count]:
                        sa_child_schedules = sa_schedules[sa_count]['child']

                        sa_child_schedules_count = len(sa_child_schedules)
                        sa_schedules_cnt += sa_child_schedules_count
                        for sa_child_count in range(sa_child_schedules_count):
                            if sa_schedules[sa_count]['child'][sa_child_count]['transactionTypeCode'] == '21B':
                                sb_schedules.append(sa_schedules[sa_count]['child'][sa_child_count])
                                sa_schedules_cnt = sa_schedules_cnt - 1
                            else:
                                sa_schedules.append(sa_schedules[sa_count]['child'][sa_child_count])
                        del sa_schedules[sa_count]['child']

                if int(len(sa_schedules) % 3) == 0:
                    sa_pages_cnt = int(len(sa_schedules) / 3)
                    sa_schedules_in_last_page = 3
                else:
                    sa_pages_cnt = int(len(sa_schedules) / 3) + 1
                    sa_schedules_in_last_page = int(len(sa_schedules) % 3)

                total_no_of_pages += sa_pages_cnt

        if 'SB' in schedules or len(sb_schedules) > 0:
            sb_start_page = total_no_of_pages + 1
            if 'SB' in schedules:
                sb_schedules.extend(schedules['SB'])
            sb_schedules_cnt = len(sb_schedules)
            if sb_schedules_cnt > 0:
                if int(sb_schedules_cnt % 3) == 0:
                    sb_pages_cnt = int(sb_schedules_cnt / 3)
                    sb_schedules_in_last_page = 3
                else:
                    sb_pages_cnt = int(sb_schedules_cnt / 3) + 1
                    sb_schedules_in_last_page = int(sb_schedules_cnt % 3)
                total_no_of_pages += sb_pages_cnt

        if sa_schedules_cnt > 0:
            has_sa_schedules = True
            schedule_total = 0.00
            os.makedirs(md5_directory + 'SA', exist_ok=True)
            sa_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SA')
            if sa_pages_cnt > 0:
                for sa_page_no in range(sa_pages_cnt):
                    page_subtotal = 0.00
                    sa_schedule_page_dict = {}
                    sa_schedule_page_dict['pageNo'] = sa_start_page + sa_page_no
                    sa_schedule_page_dict['totalPages'] = total_no_of_pages
                    page_start_index = sa_page_no * 3
                    # if sa_page_no == (sa_pages_cnt - 1):
                        # page_end_index = page_start_index + no_of_transactions_in_last_page - 1
                    sa_schedule_dict = build_sa_per_page_schedule_dict(sa_schedules_in_last_page,
                                                                       page_start_index, sa_schedule_page_dict,
                                                                       sa_schedules)
                    # else:
                    #     # no_of_transactions_in_last_page = 3
                    #     sa_schedule_dict = build_sa_per_page_schedule_dict(sa_schedules_in_last_page, page_start_index,
                    #                                                        sa_schedule_page_dict,
                    #                                                        sa_schedules)

                    page_subtotal = float(sa_schedule_page_dict['pageSubtotal'])
                    schedule_total += page_subtotal
                    if sa_pages_cnt == (sa_page_no + 1):
                        sa_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                    sa_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                    sa_schedule_page_dict['lineNumber'] = sa_schedule_dict['lineNumber']
                    sa_outfile = md5_directory + '/SA/' + 'page_' + str(sa_page_no) + '.pdf'
                    pypdftk.fill_form(sa_infile, sa_schedule_page_dict, sa_outfile)
            pypdftk.concat(directory_files(md5_directory + 'SA/'), md5_directory + 'SA/all_pages.pdf')

        if sb_schedules_cnt > 0:
            has_sb_schedules = True
            schedule_total = 0.00
            # create SA folder under MD5 directory
            os.makedirs(md5_directory + 'SB', exist_ok=True)
            sb_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SB')

            if sb_pages_cnt > 0:
                for sb_page_no in range(sb_pages_cnt):
                    page_subtotal = 0.00
                    sb_schedule_page_dict = {}
                    sb_schedule_page_dict['pageNo'] = sb_start_page + sb_page_no
                    sb_schedule_page_dict['totalPages'] = total_no_of_pages
                    page_start_index = sb_page_no * 3
                    # if sb_page_no == (sb_pages_cnt - 1):
                    sb_schedule_dict = build_sb_per_page_schedule_dict(sb_schedules_in_last_page,
                                                                    page_start_index, sb_schedule_page_dict,
                                                                    sb_schedules)
                    # else:
                    #     # no_of_transactions_in_last_page = 3
                    #     sb_schedule_dict = build_sb_per_page_schedule_dict(sb_schedules_in_last_page, page_start_index,
                    #                                                     sb_schedule_page_dict,
                    #                                                     sb_schedules)

                    page_subtotal = float(sb_schedule_page_dict['pageSubtotal'])
                    schedule_total += page_subtotal
                    if sb_pages_cnt == (sb_page_no + 1):
                        sb_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                    sb_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                    sb_schedule_page_dict['lineNumber'] = sb_schedule_dict['lineNumber']
                    sb_outfile = md5_directory + '/SB/' + 'page_' + str(sb_page_no) + '.pdf'
                    pypdftk.fill_form(sb_infile, sb_schedule_page_dict, sb_outfile)
            pypdftk.concat(directory_files(md5_directory + 'SB/'), md5_directory + 'SB/all_pages.pdf')

        return has_sa_schedules, has_sb_schedules, total_no_of_pages


    # if 'schedules' in f3x_data:
    #     schedules = f3x_data['schedules']
    #     # if 'SB' in schedules:
    #     #     sb_schedules.append(schedules['SB'])
    #     if 'SA' in schedules:
    #         sa_schedules = schedules['SA']
    #         sa_schedules_cnt = len(sa_schedules)
    #         if sa_schedules_cnt > 0:
    #             has_sa_schedules = True
    #             schedule_total = 0.00
    #             # os.remove(md5_directory + 'SA/all_pages.pdf')
    #             # create SA folder under MD5 directory
    #             os.makedirs(md5_directory + 'SA', exist_ok=True)
    #             sa_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SA')
    #
    #             for sa_count in range(sa_schedules_cnt):
    #                 if 'child' in sa_schedules[sa_count]:
    #                     sa_child_schedules = sa_schedules[sa_count]['child']
    #
    #                     sa_child_schedules_count = len(sa_child_schedules)
    #                     sa_schedules_cnt += sa_child_schedules_count
    #                     for sa_child_count in range(sa_child_schedules_count):
    #                         if sa_schedules[sa_count]['child'][sa_child_count]['transactionTypeCode'] == '21B':
    #                             sb_schedules.append(sa_schedules[sa_count]['child'][sa_child_count])
    #                             sa_schedules_cnt = sa_schedules_cnt - 1
    #                         else:
    #                             sa_schedules.append(sa_schedules[sa_count]['child'][sa_child_count])
    #                     del sa_schedules[sa_count]['child']
    #
    #             if int(len(sa_schedules) % 3) == 0:
    #                 sa_pages_cnt = int(len(sa_schedules) / 3)
    #                 no_of_transactions_in_last_page = 3
    #             else:
    #                 sa_pages_cnt = int(len(sa_schedules) / 3) + 1
    #                 no_of_transactions_in_last_page = int(len(sa_schedules) % 3)
    #
    #             total_no_of_pages += sa_pages_cnt
    #
    #             sb_schedules_cnt = len(sb_schedules)
    #             if sb_schedules_cnt > 0:
    #                 if int(sb_schedules_cnt % 3) == 0:
    #                     sb_pages_cnt = int(sb_schedules_cnt / 3)
    #                     no_of_transactions_in_last_page = 3
    #                 else:
    #                     sb_pages_cnt = int(sb_schedules_cnt / 3) + 1
    #                     no_of_transactions_in_last_page = int(sb_schedules_cnt % 3)
    #                 total_no_of_pages += sb_pages_cnt
    #
    #             if sa_pages_cnt > 0:
    #                 for sa_page_no in range(sa_pages_cnt):
    #                     page_subtotal = 0.00
    #                     sa_schedule_page_dict = {}
    #                     sa_schedule_page_dict['pageNo'] = schedule_start_page + sa_page_no
    #                     sa_schedule_page_dict['totalPages'] = total_no_of_pages
    #                     page_start_index = sa_page_no * 3
    #                     if sa_page_no == (sa_pages_cnt - 1):
    #                         # page_end_index = page_start_index + no_of_transactions_in_last_page - 1
    #                         sa_schedule_dict = build_sa_per_page_schedule_dict(no_of_transactions_in_last_page,
    #                                                                         page_start_index, sa_schedule_page_dict,
    #                                                                         sa_schedules)
    #                     else:
    #                         # no_of_transactions_in_last_page = 3
    #                         sa_schedule_dict = build_sa_per_page_schedule_dict(3, page_start_index,
    #                                                                         sa_schedule_page_dict,
    #                                                                         sa_schedules)
    #
    #                     page_subtotal = float(sa_schedule_page_dict['pageSubtotal'])
    #                     schedule_total += page_subtotal
    #                     if sa_pages_cnt == (sa_page_no + 1):
    #                         sa_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
    #                     sa_schedule_page_dict['committeeName'] = f3x_data['committeeName']
    #                     sa_schedule_page_dict['lineNumber'] = sa_schedule_dict['lineNumber']
    #                     sa_outfile = md5_directory + '/SA/' + 'page_' + str(sa_page_no) + '.pdf'
    #                     pypdftk.fill_form(sa_infile, sa_schedule_page_dict, sa_outfile)
    #             pypdftk.concat(directory_files(md5_directory + 'SA/'), md5_directory + 'SA/all_pages.pdf')
    #
    #     # process Schedule B
    #     schedule_start_page = total_no_of_pages
    #     if 'SB' in schedules:
    #         sb_schedules.append(schedules['SB'])
    #     sb_schedules_cnt = len(sb_schedules)
    #     if sb_schedules_cnt > 0:
    #         has_sb_schedules = True
    #         schedule_total = 0.00
    #         # create SA folder under MD5 directory
    #         os.makedirs(md5_directory + 'SB', exist_ok=True)
    #         sb_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SB')
    #
    #         if sb_pages_cnt > 0:
    #             for sb_page_no in range(sb_pages_cnt):
    #                 page_subtotal = 0.00
    #                 sb_schedule_page_dict = {}
    #                 sb_schedule_page_dict['pageNo'] = schedule_start_page + sb_page_no
    #                 sb_schedule_page_dict['totalPages'] = total_no_of_pages
    #                 page_start_index = sb_page_no * 3
    #                 if sb_page_no == (sb_pages_cnt - 1):
    #                     sb_schedule_dict = build_sb_per_page_schedule_dict(no_of_transactions_in_last_page,
    #                                                                     page_start_index, sb_schedule_page_dict,
    #                                                                     sb_schedules)
    #                 else:
    #                     # no_of_transactions_in_last_page = 3
    #                     sb_schedule_dict = build_sb_per_page_schedule_dict(3, page_start_index,
    #                                                                     sb_schedule_page_dict,
    #                                                                     sb_schedules)
    #
    #                 page_subtotal = float(sb_schedule_page_dict['pageSubtotal'])
    #                 schedule_total += page_subtotal
    #                 if sb_pages_cnt == (sb_page_no + 1):
    #                     sb_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
    #                 sb_schedule_page_dict['committeeName'] = f3x_data['committeeName']
    #                 sb_schedule_page_dict['lineNumber'] = sb_schedule_dict['lineNumber']
    #                 sb_outfile = md5_directory + '/SB/' + 'page_' + str(sb_page_no) + '.pdf'
    #                 pypdftk.fill_form(sb_infile, sb_schedule_page_dict, sb_outfile)
    #         pypdftk.concat(directory_files(md5_directory + 'SB/'), md5_directory + 'SB/all_pages.pdf')
    # return has_sa_schedules, has_sb_schedules, total_no_of_pages


def build_sa_per_page_schedule_dict(no_of_transactions_in_last_page, page_start_index, sa_schedule_page_dict,
                                 sa_schedules):
    page_subtotal = 0.00
    if no_of_transactions_in_last_page == 1:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
    elif no_of_transactions_in_last_page == 2:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 1]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
    elif no_of_transactions_in_last_page == 3:
        index = 1
        contributor_name = []
        sa_schedule_dict = sa_schedules[page_start_index + 0]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 1]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 3
        contributor_name.clear()
        sa_schedule_dict = sa_schedules[page_start_index + 2]
        if sa_schedule_dict['memoCode'] != 'X':
            page_subtotal += sa_schedule_dict['contributionAmount']
        for key in sa_schedules[page_start_index]:
            build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name)
        sa_schedule_page_dict["contributorName_"+str(index)] = ",".join(map(str, contributor_name))
    sa_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    return sa_schedule_dict


def build_sb_per_page_schedule_dict(no_of_transactions_in_last_page, page_start_index, sb_schedule_page_dict,
                                 sb_schedules):
    page_subtotal = 0.00
    if no_of_transactions_in_last_page == 1:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
    elif no_of_transactions_in_last_page == 2:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 1]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
    elif no_of_transactions_in_last_page == 3:
        index = 1
        contributor_name = []
        sb_schedule_dict = sb_schedules[page_start_index + 0]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 2
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 1]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
        index = 3
        contributor_name.clear()
        sb_schedule_dict = sb_schedules[page_start_index + 2]
        if sb_schedule_dict['memoCode'] != 'X':
            page_subtotal += sb_schedule_dict['expenditureAmount']
        for key in sb_schedules[page_start_index]:
            build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, contributor_name)
        sb_schedule_page_dict["payeeName_"+str(index)] = ",".join(map(str, contributor_name))
    sb_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    return sb_schedule_dict


def build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict, contributor_name):
    if not sa_schedule_dict[key]:
        sa_schedule_dict[key] = ""
    if key == 'contributorLastName':
        contributor_name.append(sa_schedule_dict[key])
    elif key == 'contributorFirstName':
        contributor_name.append(sa_schedule_dict[key])
    elif key == 'contributorMiddleName':
        contributor_name.append(sa_schedule_dict[key])
    elif key == 'contributorPrefix':
        contributor_name.append(sa_schedule_dict[key])
    elif key == 'contributorSuffix':
        contributor_name.append(sa_schedule_dict[key])
    elif key == 'contributionDate':
        date_array = sa_schedule_dict[key].split("/")
        sa_schedule_page_dict['contributionDateMonth_' + str(index)] = date_array[0]
        sa_schedule_page_dict['contributionDateDay_' + str(index)] = date_array[1]
        sa_schedule_page_dict['contributionDateYear_' + str(index)] = date_array[2]
    else:
        if key == 'contributionAmount' or key == 'contributionAggregate':
            sa_schedule_page_dict[key + '_' + str(index)] = '{0:.2f}'.format(sa_schedule_dict[key])
        else:
            sa_schedule_page_dict[key + '_' + str(index)] = sa_schedule_dict[key]


def build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict, payee_name):
    if not sb_schedule_dict[key]:
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
