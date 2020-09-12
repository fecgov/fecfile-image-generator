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

from routes.src.form3x import calculate_page_count, calculate_memo_page_count


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
def get_summary_detail(f3l_summary, f3l_data, f3l_data_summary):
    # check if semmianual start and end date is there set row 5 and row 6 of summary page
    if f3l_data['semi_annual_start_date'] and len(f3l_data['semi_annual_start_date']) > 0:
        semi_annual_start_date_array = f3l_data['semi_annual_start_date'].split("-")
        f3l_data['semiAnnualStartDateMonth'] = semi_annual_start_date_array[0]
        f3l_data['semiAnnualStartDateDay'] = semi_annual_start_date_array[1]
        f3l_data['semiAnnualStartDateYear'] = semi_annual_start_date_array[2]

        semi_annual_end_date_array = f3l_data['semi_annual_end_date'].split("-")
        f3l_data['semiAnnualEndDateMonth'] = semi_annual_end_date_array[0]
        f3l_data['semiAnnualEndDateDay'] = semi_annual_end_date_array[1]
        f3l_data['semiAnnualEndDateYear'] = semi_annual_end_date_array[2]

        if int(semi_annual_start_date_array[1]) < 6:
            f3l_data_summary['semiAnnualPeriod_6b_H1'] = 'X'
        else:
            f3l_data_summary['semiAnnualPeriod_6b_H2'] = 'X'

    f3l_data_summary['amendmentIndicator'] = f3l_data['amend_indicator']

    if f3l_summary['contribute_amount_query'] and len(f3l_summary['contribute_amount_query']) > 0:
        f3l_amount = f3l_summary['contribute_amount_query']
        f3l_data_summary['quarterly_monthly_total'] = f3l_amount['quarterly_monthly_total']
        f3l_data_summary['semi_annual_total'] = f3l_amount['semi_annual_total']


def print_pdftk(stamp_print):
    # check if json_file is in the request
    # try:
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
        infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F3L')
        # save json file as md5 file name
        json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
        outfile = md5_directory + json_file_md5 + '_temp.pdf'
        # load json file
        f3l_json = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
        # setting timestamp and imgno to empty as these needs to show up after submission
        output = {}
        if stamp_print != 'stamp':
            output['FILING_TIMESTAMP'] = ''
            output['IMGNO'] = ''

        # read data from json file
        f3l_data = f3l_json['data']

        # check if summary is present in fecDataFile
        f3l_summary = []
        if 'summary' in f3l_data:
            f3l_summary = f3l_data['summary']

        # split coverage start date and coverage end date to set month, day, and year
        coverage_start_date_array = f3l_data['coverageStartDate'].split("/")
        f3l_data['coverageStartDateMonth'] = coverage_start_date_array[0]
        f3l_data['coverageStartDateDay'] = coverage_start_date_array[1]
        f3l_data['coverageStartDateYear'] = coverage_start_date_array[2]

        coverage_end_date_array = f3l_data['coverageEndDate'].split("/")
        f3l_data['coverageEndDateMonth'] = coverage_end_date_array[0]
        f3l_data['coverageEndDateDay'] = coverage_end_date_array[1]
        f3l_data['coverageEndDateYear'] = coverage_end_date_array[2]

        # checking for signed date, it is only available for submitted reports
        if f3l_data['date_signed'] and len(f3l_data['date_signed']) > 0:
            date_signed_array = f3l_data['date_signed'].split("/")
            f3l_data['dateSignedMonth'] = date_signed_array[0]
            f3l_data['dateSignedDay'] = date_signed_array[1]
            f3l_data['dateSignedYear'] = date_signed_array[2]

        # build treasurer name to map it to PDF template
        treasurer_full_name = []
        treasurer_full_name.append(f3l_data['treasurerLastName'])
        treasurer_full_name.append(f3l_data['treasurerFirstName'])
        treasurer_full_name.append(f3l_data['treasurerMiddleName'])
        treasurer_full_name.append(f3l_data['treasurerPrefix'])
        treasurer_full_name.append(f3l_data['treasurerSuffix'])
        f3l_data['treasurerFullName'] = ",".join(map(str, treasurer_full_name))
        f3l_data['treasurerName'] = f3l_data['treasurerLastName'] + "," + f3l_data['treasurerFirstName']
        f3l_data['efStamp'] = '[Electronically Filed]'

        # checking if json contains summary details, for individual transactions print there wouldn't be summary
        if len(f3l_summary) > 0:
            total_no_of_pages = 1
            f3l_data_summary_array = [f3l_data, f3l_summary]
            if 'memoText' in f3l_data and f3l_data['memoText']:
                total_no_of_pages += 1
        else:
            f3l_data_summary_array = [f3l_data]
        f3l_data_summary = {i: j for x in f3l_data_summary_array for i, j in x.items()}

        # process all schedules and build the PDF's
        process_output, total_no_of_pages = process_schedules(f3l_data, md5_directory, total_no_of_pages)

        has_sa_schedules = process_output.get('has_sa_schedules')
        has_sb_schedules = process_output.get('has_sb_schedules')

        if len(f3l_summary) > 0:
            get_summary_detail(f3l_summary, f3l_data, f3l_data_summary)
            f3l_data_summary['PAGESTR'] = "PAGE " + str(page_no) + " / " + str(total_no_of_pages)
            pypdftk.fill_form(infile, f3l_data_summary, outfile)
            shutil.copy(outfile, md5_directory + 'F3L_Summary.pdf')
            os.remove(md5_directory + json_file_md5 + '_temp.pdf')
            # Memo text changes
            if 'memoText' in f3l_data_summary and f3l_data_summary['memoText']:
                memo_dict = {}
                temp_memo_outfile = md5_directory + 'F3L_Summary_memo.pdf'
                memo_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
                memo_dict['scheduleName_1'] = 'F3L' + f3l_data_summary['amendmentIndicator']
                memo_dict['memoDescription_1'] = f3l_data_summary['memoText']
                memo_dict['PAGESTR'] = "PAGE " + str(2) + " / " + str(total_no_of_pages)
                pypdftk.fill_form(memo_infile, memo_dict, temp_memo_outfile)
                pypdftk.concat([md5_directory + 'F3L_Summary.pdf', temp_memo_outfile], md5_directory +
                               json_file_md5 + '_temp.pdf')
                shutil.copy(md5_directory + json_file_md5 + '_temp.pdf', md5_directory + 'F3L_Summary.pdf')
                os.remove(md5_directory + json_file_md5 + '_temp.pdf')

            # check if all_pages already exsits
            if os.path.exists(md5_directory + 'all_pages.pdf'):
                os.remove(md5_directory + 'all_pages.pdf')

            # checking for sa transactions
            if has_sa_schedules:
                pypdftk.concat([md5_directory + 'F3L_Summary.pdf', md5_directory + 'SA/all_pages.pdf'],
                               md5_directory + 'all_pages.pdf')
                os.remove(md5_directory + 'SA/all_pages.pdf')
                shutil.rmtree(md5_directory + 'SA')
            else:
                shutil.copy(md5_directory + 'F3L_Summary.pdf', md5_directory + 'all_pages.pdf')

            # checking for sb transactions
            if has_sb_schedules:
                pypdftk.concat([md5_directory + 'all_pages.pdf', md5_directory + 'SB/all_pages.pdf'],
                               md5_directory + 'temp_all_pages.pdf')
                shutil.move(md5_directory + 'temp_all_pages.pdf', md5_directory + 'all_pages.pdf')
                os.remove(md5_directory + 'SB/all_pages.pdf')
                shutil.rmtree(md5_directory + 'SB')

        else:
            # no summary, expecting it to be from individual transactions
            if has_sa_schedules:
                if os.path.exists(md5_directory + 'all_pages.pdf'):
                    os.remove(md5_directory + 'all_pages.pdf')
                    shutil.move(md5_directory + 'SA/all_pages.pdf', md5_directory + 'all_pages.pdf')
                else:
                    shutil.move(md5_directory + 'SA/all_pages.pdf', md5_directory + 'all_pages.pdf')
                shutil.rmtree(md5_directory + 'SA')

            if has_sb_schedules:
                if os.path.exists(md5_directory + 'all_pages.pdf'):
                    os.remove(md5_directory + 'all_pages.pdf')
                    shutil.move(md5_directory + 'SB/all_pages.pdf', md5_directory + 'all_pages.pdf')
                else:
                    shutil.move(md5_directory + 'SB/all_pages.pdf', md5_directory + 'all_pages.pdf')
                shutil.rmtree(md5_directory + 'SB')

                # push output file to AWS
                s3 = boto3.client('s3')
                s3.upload_file(md5_directory + 'all_pages.pdf',
                               current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
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


def process_schedules(f3l_data, md5_directory, total_no_of_pages):
    # Calculate total number of pages for schedules
    sb_line_numbers = ['21B', '22', '23', '26', '27', '28A', '28B', '28C', '29', '30B']
    sa_line_numbers = []
    sa_schedules = []
    sb_schedules = []

    has_sa_schedules = has_sb_schedules = False

    sa_schedules_cnt = sb_schedules_cnt = 0

    # check if schedules exist in data file
    if 'schedules' in f3l_data:
        schedules = f3l_data['schedules']

        if 'SA' in schedules:
            sa_start_page = total_no_of_pages
            sa_schedules = schedules.get('SA')
            sa_schedules_cnt = len(sa_schedules)

            # if sa_schedules_cnt > 0:
            if sa_schedules:
                has_sa_schedules = True
                os.makedirs(md5_directory + 'SA', exist_ok=True)
                # building array for all SA line numbers
                sa_11a = []
                sa_11a_memo = []

                sa_11a_last_page_cnt = 4
                sa_11a_memo_last_page_cnt = 2
                sa_11a_page_cnt = sa_11a_memo_page_cnt = 0

                # process for each Schedule A
                sa_schedules_cnt = len(sa_schedules)
                for sa_count in range(sa_schedules_cnt):
                    process_sa_line_numbers(sa_11a, sa_11a_memo, sa_schedules[sa_count])

                # calculate number of pages for SA line numbers
                sa_11a_page_cnt, sa_11a_last_page_cnt = calculate_sa_page_count(sa_11a)
                sa_11a_memo_page_cnt, sa_11a_memo_last_page_cnt = calculate_memo_page_count(sa_11a_memo)

                # calculate total number of pages
                total_no_of_pages = (total_no_of_pages + sa_11a_page_cnt + sa_11a_memo_page_cnt)
                sb_start_page = total_no_of_pages

                # checking for SB transactions
        if 'SB' in schedules:

            sb_start_page = total_no_of_pages
            sb_schedules.extend(schedules['SB'])
            sb_schedules_cnt = len(sb_schedules)

            if sb_schedules_cnt > 0:
                has_sb_schedules = True
                os.makedirs(md5_directory + 'SB', exist_ok=True)
                # building array for all SB line numbers
                sb_17 = []
                sb_17_memo = []

                sb_17_last_page_cnt = 5
                sb_15_memo_last_page_cnt = 2
                sb_17_page_cnt = sb_17_memo_page_cnt = 0

                # process for each Schedule B
                for sb_count in range(sb_schedules_cnt):
                    process_sb_line_numbers(sb_17, sb_17_memo, sb_schedules[sb_count])

                sb_17_page_cnt, sb_17_last_page_cnt = calculate_sb_page_count(sb_17)
                sb_17_memo_page_cnt, sb_17_memo_last_page_cnt = calculate_memo_page_count(sb_17_memo)

                total_no_of_pages = (total_no_of_pages + sb_17_page_cnt + sb_17_memo_page_cnt)

        if sa_schedules_cnt > 0:
            # process Schedule 11AI
            sa_11a_start_page = sa_start_page
            process_sa_line(f3l_data, md5_directory, '3L', sa_11a, sa_11a_page_cnt, sa_11a_start_page,
                            sa_11a_last_page_cnt, total_no_of_pages)
            sa_11a_memo_start_page = sa_11a_start_page + sa_11a_page_cnt

        if sb_schedules_cnt > 0:
            # process Schedule 21B
            sb_17_start_page = sb_start_page
            process_sb_line(f3l_data, md5_directory, '3L', sb_17, sb_17_page_cnt, sb_17_start_page,
                            sb_17_last_page_cnt, total_no_of_pages)

    output_data = {
        'has_sa_schedules': has_sa_schedules,
        'has_sb_schedules': has_sb_schedules
    }

    return output_data, total_no_of_pages


# except Exception as e:
# 	return error('Error generating print preview, error message: ' + str(e))

# This method is invoked for each SB line number, it builds PDF for line numbers
def process_sb_line(f3x_data, md5_directory, line_number, sb_line, sb_line_page_cnt, sb_line_start_page,
                    sb_line_last_page_cnt, total_no_of_pages):
    has_sb_schedules = False
    if len(sb_line) > 0:
        schedule_total = 0.00
        schedule_aggregate_total = 0.00
        os.makedirs(md5_directory + 'SB/' + line_number, exist_ok=True)
        sb_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SB3L')
        if sb_line_page_cnt > 0:
            sb_line_start_page += 1
            for sb_page_no in range(sb_line_page_cnt):
                page_subtotal = 0.00
                memo_array = []
                last_page = False
                sb_schedule_page_dict = {}
                sb_schedule_page_dict['lineNumber'] = line_number
                sb_schedule_page_dict['pageNo'] = sb_line_start_page + sb_page_no
                sb_schedule_page_dict['totalPages'] = total_no_of_pages
                page_start_index = sb_page_no * 5
                if ((sb_page_no + 1) == sb_line_page_cnt):
                    last_page = True
                # This call prepares data to render on PDF
                sb_schedule_dict = build_sb_per_page_schedule_dict(last_page, sb_line_last_page_cnt,
                                                                   page_start_index, sb_schedule_page_dict,
                                                                   sb_line, memo_array)

                page_subtotal = float(sb_schedule_page_dict['pageSubtotal'])
                page_aggregate_total = float(sb_schedule_page_dict['pageAggSubtotal'])
                schedule_total += page_subtotal
                schedule_aggregate_total += page_aggregate_total
                if sb_line_page_cnt == (sb_page_no + 1):
                    sb_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                    sb_schedule_page_dict['scheduleAggTotal'] = '{0:.2f}'.format(schedule_aggregate_total)
                sb_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                sb_outfile = md5_directory + 'SB/' + line_number + '/page_' + str(sb_page_no) + '.pdf'
                pypdftk.fill_form(sb_infile, sb_schedule_page_dict, sb_outfile)
                # Memo text changes
                memo_dict = {}
                if len(memo_array) >= 1:
                    temp_memo_outfile = md5_directory + 'SB/' + line_number + '/page_memo_temp.pdf'
                    memo_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
                    memo_outfile = md5_directory + 'SB/' + line_number + '/page_memo_' + str(sb_page_no) + '.pdf'
                    memo_dict['scheduleName_1'] = memo_array[0]['scheduleName']
                    memo_dict['memoDescription_1'] = memo_array[0]['memoDescription']
                    memo_dict['transactionId_1'] = memo_array[0]['transactionId']
                    if len(memo_array) >= 2:
                        memo_dict['scheduleName_2'] = memo_array[1]['scheduleName']
                        memo_dict['memoDescription_2'] = memo_array[1]['memoDescription']
                        memo_dict['transactionId_2'] = memo_array[1]['transactionId']
                    # build page
                    pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                    pypdftk.concat([sb_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, sb_outfile)
                    sb_line_start_page += 1

                    if len(memo_array) >= 3:
                        memo_dict = {}
                        memo_outfile = md5_directory + 'SB/' + line_number + '/page_memo_' + str(sb_page_no) + '.pdf'
                        memo_dict['scheduleName_1'] = memo_array[2]['scheduleName']
                        memo_dict['memoDescription_1'] = memo_array[2]['memoDescription']
                        memo_dict['transactionId_1'] = memo_array[2]['transactionId']
                        if len(memo_array) >= 4:
                            memo_dict['scheduleName_2'] = memo_array[3]['scheduleName']
                            memo_dict['memoDescription_2'] = memo_array[3]['memoDescription']
                            memo_dict['transactionId_2'] = memo_array[3]['transactionId']
                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([sb_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, sb_outfile)
                        sb_line_start_page += 1

                    if len(memo_array) >= 5:
                        memo_dict = {}
                        memo_outfile = md5_directory + 'SB/' + line_number + '/page_memo_' + str(sb_page_no) + '.pdf'
                        memo_dict['scheduleName_1'] = memo_array[4]['scheduleName']
                        memo_dict['memoDescription_1'] = memo_array[4]['memoDescription']
                        memo_dict['transactionId_1'] = memo_array[4]['transactionId']
                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([sb_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, sb_outfile)
                        sb_line_start_page += 1
        pypdftk.concat(directory_files(md5_directory + 'SB/' + line_number + '/'), md5_directory + 'SB/' + line_number
                       + '/all_pages.pdf')
        if path.isfile(md5_directory + 'SB/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SB/all_pages.pdf', md5_directory + 'SB/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SB/temp_all_pages.pdf')
            os.rename(md5_directory + 'SB/temp_all_pages.pdf', md5_directory + 'SB/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SB/' + line_number + '/all_pages.pdf', md5_directory + 'SB/all_pages.pdf')
    return has_sb_schedules


# This method builds data for individual SB page
def build_sb_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, sb_schedule_page_dict,
                                    sb_schedules, memo_array):
    page_subtotal = 0.00
    page_arg_subtotal = 0.00
    if not last_page:
        transactions_in_page = 5

    if transactions_in_page == 1:
        for i in range(1):
            page_arg_subtotal, page_subtotal, sb_schedule_dict = building_sb_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sb_schedule_page_dict, sb_schedules,
                                                                                   page_subtotal)
    elif transactions_in_page == 2:
        for i in range(2):
            page_arg_subtotal, page_subtotal, sb_schedule_dict = building_sb_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sb_schedule_page_dict, sb_schedules,
                                                                                   page_subtotal)
    elif transactions_in_page == 3:
        for i in range(3):
            page_arg_subtotal, page_subtotal, sb_schedule_dict = building_sb_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sb_schedule_page_dict, sb_schedules,
                                                                                   page_subtotal)

    elif transactions_in_page == 4:
        for i in range(4):
            page_arg_subtotal, page_subtotal, sb_schedule_dict = building_sb_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sb_schedule_page_dict, sb_schedules,
                                                                                   page_subtotal)

    elif transactions_in_page == 5:
        for i in range(5):
            page_arg_subtotal, page_subtotal, sb_schedule_dict = building_sb_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sb_schedule_page_dict, sb_schedules,
                                                                                   page_subtotal)
    sb_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    sb_schedule_page_dict['pageAggSubtotal'] = '{0:.2f}'.format(page_arg_subtotal)
    return sb_schedule_dict


def building_sb_index(i, memo_array, page_start_index, page_arg_subtotal, sb_schedule_page_dict, sb_schedules,
                      page_subtotal):
    index = i
    sb_schedule_dict = sb_schedules[page_start_index + i - 1]
    process_memo_text(sb_schedule_dict, 'SB', memo_array)
    if sb_schedule_dict['expenditureAggregate'] != '':
        page_arg_subtotal += sb_schedule_dict['expenditureAggregate']
    if sb_schedule_dict['expenditureAmount'] != '':
        page_subtotal += sb_schedule_dict['expenditureAmount']
    build_payee_name_date_dict(index, page_start_index, sb_schedule_dict, sb_schedule_page_dict)
    return page_arg_subtotal, page_subtotal, sb_schedule_dict


def build_payee_name_date_dict(index, key, sb_schedule_dict, sb_schedule_page_dict):
    try:

        if 'payeeLastName' in sb_schedule_dict and sb_schedule_dict['payeeLastName']:
            sb_schedule_page_dict['payeeName_' + str(index)] = (sb_schedule_dict['payeeLastName'] + ','
                                                                + sb_schedule_dict['payeeFirstName'] + ','
                                                                + sb_schedule_dict['payeeMiddleName'] + ','
                                                                + sb_schedule_dict['payeePrefix'] + ','
                                                                + sb_schedule_dict['payeeSuffix'])
        elif 'payeeOrganizationName' in sb_schedule_dict:
            sb_schedule_page_dict["payeeName_" + str(index)] = sb_schedule_dict['payeeOrganizationName']

        if 'beneficiaryCandidateLastName' in sb_schedule_dict and sb_schedule_dict['beneficiaryCandidateLastName']:
            sb_schedule_page_dict['beneficiaryName_' + str(index)] = (
                    sb_schedule_dict['beneficiaryCandidateLastName'] + ','
                    + sb_schedule_dict['beneficiaryCandidateFirstName'] + ','
                    + sb_schedule_dict['beneficiaryCandidateMiddleName'] + ','
                    + sb_schedule_dict['beneficiaryCandidatePrefix'] + ','
                    + sb_schedule_dict['beneficiaryCandidateSuffix'])

        if 'expenditureAmount' in sb_schedule_dict:
            if sb_schedule_dict['expenditureAmount'] == '':
                sb_schedule_dict['expenditureAmount'] = 0.0
            sb_schedule_page_dict['expenditureAmount_' + str(index)] = '{0:.2f}'.format(
                sb_schedule_dict['expenditureAmount'])
            del sb_schedule_dict['expenditureAmount']

        if 'expenditureAggregate' in sb_schedule_dict:
            if sb_schedule_dict['expenditureAggregate'] == '':
                sb_schedule_dict['expenditureAggregate'] = 0.0
            sb_schedule_page_dict['expenditureAggregate_' + str(index)] = '{0:.2f}'.format(
                sb_schedule_dict['expenditureAggregate'])
            del sb_schedule_dict['expenditureAggregate']

        for key in sb_schedule_dict:
            if key != 'lineNumber':
                sb_schedule_page_dict[key + '_' + str(index)] = sb_schedule_dict[key]
    except Exception as e:
        print('Error at key: ' + key + ' in Schedule A transaction: ' + str(sb_schedule_dict))
        raise e


# This method is invoked for each SA line number, it builds PDF for line numbers
def process_sa_line(f3l_data, md5_directory, line_number, sa_line, sa_line_page_cnt, sa_line_start_page,
                    sa_line_last_page_cnt, total_no_of_pages):
    has_sa_schedules = False
    if len(sa_line) > 0:
        sa_line_start_page += 1
        has_sa_schedules = True
        schedule_total = 0.00
        schedule_aggregate_total = 0.00
        os.makedirs(md5_directory + 'SA/' + line_number, exist_ok=True)
        sa_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SA3L')
        if sa_line_page_cnt > 0:
            for sa_page_no in range(sa_line_page_cnt):

                # if sa_schedule_page_dict['memoDescription']:
                #     sa_memo_obj = {'memoDescripton':sa_schedule_page_dict['memoDescription'], 'transactionId': sa_schedule_page_dict['transactionId']}
                #     sa_memo.append(sa_memo_obj)
                page_subtotal = 0.00
                memo_array = []
                last_page = False
                sa_schedule_page_dict = {}
                sa_schedule_page_dict['lineNumber'] = line_number
                sa_schedule_page_dict['pageNo'] = sa_line_start_page + sa_page_no
                sa_schedule_page_dict['totalPages'] = total_no_of_pages
                page_start_index = sa_page_no * 4
                if ((sa_page_no + 1) == sa_line_page_cnt):
                    last_page = True
                # This call prepares data to render on PDF

                sa_schedule_dict = build_sa_per_page_schedule_dict(last_page, sa_line_last_page_cnt,
                                                                   page_start_index, sa_schedule_page_dict,
                                                                   sa_line, memo_array)

                page_subtotal = float(sa_schedule_page_dict['pageSubtotal'])
                page_aggregate_total = float(sa_schedule_page_dict['pageAggSubtotal'])
                schedule_total += page_subtotal
                schedule_aggregate_total += page_aggregate_total
                if sa_line_page_cnt == (sa_page_no + 1):
                    sa_schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)
                    sa_schedule_page_dict['scheduleAggTotal'] = '{0:.2f}'.format(page_aggregate_total)
                sa_schedule_page_dict['committeeName'] = f3l_data['committeeName']
                sa_outfile = md5_directory + 'SA/' + line_number + '/page_' + str(sa_page_no) + '.pdf'
                pypdftk.fill_form(sa_infile, sa_schedule_page_dict, sa_outfile)
                # Memo text changes
                memo_dict = {}
                if len(memo_array) >= 1:
                    temp_memo_outfile = md5_directory + 'SA/' + line_number + '/page_memo_temp.pdf'
                    memo_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
                    memo_outfile = md5_directory + 'SA/' + line_number + '/page_memo_' + str(sa_page_no) + '.pdf'
                    memo_dict['scheduleName_1'] = memo_array[0]['scheduleName']
                    memo_dict['memoDescription_1'] = memo_array[0]['memoDescription']
                    memo_dict['transactionId_1'] = memo_array[0]['transactionId']
                    if len(memo_array) >= 2:
                        memo_dict['scheduleName_2'] = memo_array[1]['scheduleName']
                        memo_dict['memoDescription_2'] = memo_array[1]['memoDescription']
                        memo_dict['transactionId_2'] = memo_array[1]['transactionId']
                    # build page
                    pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                    pypdftk.concat([sa_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, sa_outfile)
                    sa_line_start_page += 1

                    if len(memo_array) >= 3:
                        memo_dict = {}
                        memo_outfile = md5_directory + 'SA/' + line_number + '/page_memo_' + str(sa_page_no) + '.pdf'
                        memo_dict['scheduleName_1'] = memo_array[2]['scheduleName']
                        memo_dict['memoDescription_1'] = memo_array[2]['memoDescription']
                        memo_dict['transactionId_1'] = memo_array[2]['transactionId']
                        if len(memo_array) >= 4:
                            memo_dict['scheduleName_2'] = memo_array[3]['scheduleName']
                            memo_dict['memoDescription_2'] = memo_array[3]['memoDescription']
                            memo_dict['transactionId_2'] = memo_array[3]['transactionId']

                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([sa_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, sa_outfile)
                        sa_line_start_page += 1
        pypdftk.concat(directory_files(md5_directory + 'SA/' + line_number + '/'), md5_directory + 'SA/' + line_number
                       + '/all_pages.pdf')
        # if len(sa_memo) > 0:
        #     for sa_memo_obj in range(sa_memo):
        #         sa_outfile = md5_directory + 'SA/' + line_number + '/page_' + str(sa_page_no) + '.pdf'
        #         pypdftk.fill_form(sa_infile, sa_schedule_page_dict, sa_outfile)

        # if all_pages.pdf exists in SA folder, concatenate line number pdf to all_pages.pdf
        if path.isfile(md5_directory + 'SA/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SA/all_pages.pdf', md5_directory + 'SA/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SA/temp_all_pages.pdf')
            os.rename(md5_directory + 'SA/temp_all_pages.pdf', md5_directory + 'SA/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SA/' + line_number + '/all_pages.pdf', md5_directory + 'SA/all_pages.pdf')
    return has_sa_schedules


# This method builds data for individual SA page
def build_sa_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, sa_schedule_page_dict,
                                    sa_schedules, memo_array):
    page_arg_subtotal = 0.00
    page_subtotal = 0.00
    if not last_page:
        transactions_in_page = 4

    if transactions_in_page == 1:
        for i in range(1):
            page_arg_subtotal, sa_schedule_dict, page_subtotal = building_sa_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sa_schedule_page_dict, sa_schedules,
                                                                                   page_subtotal)
    elif transactions_in_page == 2:
        for i in range(2):
            page_arg_subtotal, sa_schedule_dict, page_subtotal = building_sa_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sa_schedule_page_dict, sa_schedules,
                                                                                   page_subtotal)
    elif transactions_in_page == 3:
        for i in range(3):
            page_arg_subtotal, sa_schedule_dict, page_subtotal = building_sa_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sa_schedule_page_dict, sa_schedules,
                                                                                   page_subtotal)
    elif transactions_in_page == 4:
        for i in range(4):
            page_arg_subtotal, sa_schedule_dict, page_subtotal = building_sa_index(i + 1, memo_array, page_start_index,
                                                                                   page_arg_subtotal,
                                                                                   sa_schedule_page_dict, sa_schedules,
                                                                                   page_subtotal)
    sa_schedule_page_dict['pageAggSubtotal'] = '{0:.2f}'.format(page_arg_subtotal)
    sa_schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)
    return sa_schedule_dict


def building_sa_index(i, memo_array, page_start_index, page_arg_subtotal, sa_schedule_page_dict, sa_schedules,
                      page_subtotal):
    index = i
    sa_schedule_dict = sa_schedules[page_start_index + i - 1]
    process_memo_text(sa_schedule_dict, 'SA', memo_array)
    if sa_schedule_dict['contributionAggregate'] != '':
        page_arg_subtotal += sa_schedule_dict['contributionAggregate']
    if sa_schedule_dict['contributionAmount'] != '':
        page_subtotal += sa_schedule_dict['contributionAmount']
    build_contributor_name_date_dict(index, page_start_index, sa_schedule_dict, sa_schedule_page_dict)
    return page_arg_subtotal, sa_schedule_dict, page_subtotal


# This method filters data and message data to render PDF
def build_contributor_name_date_dict(index, key, sa_schedule_dict, sa_schedule_page_dict):
    try:
        if 'contributorLastName' in sa_schedule_dict and sa_schedule_dict['contributorLastName']:
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
            if key != 'lineNumber':
                sa_schedule_page_dict[key + '_' + str(index)] = sa_schedule_dict[key]
    except Exception as e:
        print('Error at key: ' + key + ' in Schedule A transaction: ' + str(sa_schedule_dict))
        raise e


def process_memo_text(schedule_dict, schedule, memo_array):
    if 'memoDescription' in schedule_dict and schedule_dict['memoDescription']:
        memo_array.append(
            {'scheduleName': schedule + schedule_dict['lineNumber'],
             'memoDescription': schedule_dict['memoDescription'],
             'transactionId': schedule_dict['transactionId']})


def calculate_sa_page_count(schedules):
    schedules_cnt = len(schedules)
    if int(schedules_cnt % 4) == 0:
        pages_cnt = int(schedules_cnt / 4)
        schedules_in_last_page = 4
    else:
        pages_cnt = int(schedules_cnt / 4) + 1
        schedules_in_last_page = int(schedules_cnt % 4)
    return pages_cnt, schedules_in_last_page


def calculate_sb_page_count(schedules):
    schedules_cnt = len(schedules)
    if int(schedules_cnt % 5) == 0:
        pages_cnt = int(schedules_cnt / 5)
        schedules_in_last_page = 5
    else:
        pages_cnt = int(schedules_cnt / 5) + 1
        schedules_in_last_page = int(schedules_cnt % 5)
    return pages_cnt, schedules_in_last_page


def process_sa_line_numbers(sa_11a, sa_11a_memo, sa_obj):
    if sa_obj['lineNumber'] == '3L':
        sa_11a.append(sa_obj)
        if sa_obj['memoDescription']:
            sa_11a_memo.append(
                {'scheduleName': 'SA' + sa_obj['lineNumber'], 'memoDescription': sa_obj['memoDescription'],
                 'transactionId': sa_obj['transactionId']})


def process_sb_line_numbers(sb_17, sa_17_memo, sb_obj):
    if sb_obj['lineNumber'] == '3L':
        sb_17.append(sb_obj)
        if sb_obj['memoDescription']:
            sa_17_memo.append(
                {'scheduleName': 'SB' + sb_obj['lineNumber'], 'memoDescription': sb_obj['memoDescription'],
                 'transactionId': sb_obj['transactionId']})


def print_f24(print_dict, page_index, reportId, json_file_md5):
    try:
        md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
        infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F24')
        outfile = md5_directory + json_file_md5 + '_temp.pdf'
        pypdftk.fill_form(infile, print_dict, outfile)
        shutil.copy(outfile, md5_directory + reportId + '/F24_{}.pdf'.format(page_index))
        os.remove(outfile)
    except Exception as e:
        return error('print_f24 error, error message: ' + str(e))


def print_summ(print_dict, page_index, reportId, json_file_md5):
    try:
        md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
        infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
        outfile = md5_directory + json_file_md5 + '_temp.pdf'
        pypdftk.fill_form(infile, print_dict, outfile)
        shutil.copy(outfile, md5_directory + reportId + '/F24_{}.pdf'.format(page_index))
        os.remove(outfile)
    except Exception as e:
        return error('print_f24_summ error, error message: ' + str(e))
