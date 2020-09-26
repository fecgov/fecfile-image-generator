import os
import pypdftk

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text, build_sh_name_date_dict, build_memo_page
from routes.src.utils import directory_files


def print_sh6_line(f3x_data, md5_directory, line_number, sh6_list, page_cnt, start_page,
                    total_no_of_pages):
    if sh6_list:
        last_page_cnt = 3 if len(sh6_list) % 3 == 0 else len(sh6_list) % 3
        current_page_num = start_page + 1
        total_federal_share = 0
        total_levin_share = 0
        total_fed_levin_share = 0

        os.makedirs(md5_directory + 'SH6/' + line_number, exist_ok=True)
        sh6_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SH6')

        for page_num in range(page_cnt):
            current_page_num += page_num
            page_subtotal = 0
            memo_array = []
            last_page = False
            schedule_page_dict = {}
            schedule_page_dict['lineNumber'] = line_number
            schedule_page_dict['pageNo'] = current_page_num
            schedule_page_dict['totalPages'] = total_no_of_pages
            page_start_index = page_num * 3
            if page_num + 1 == page_cnt:
                last_page = True

            # This call prepares data to render on PDF
            build_sh6_line_per_page_schedule_dict(last_page, last_page_cnt,
                                                page_start_index, schedule_page_dict,
                                                sh6_list, memo_array)

            page_fed_subtotal = float(schedule_page_dict['subTotalFederalShare'])
            page_levin_subtotal = float(schedule_page_dict['subTotalLevinShare'])

            schedule_page_dict['fedLevinSubTotalShare'] = page_fed_subtotal+page_levin_subtotal

            total_federal_share += page_fed_subtotal
            total_levin_share += page_levin_subtotal
            if page_cnt == page_num + 1:
                schedule_page_dict['totalFederalShare'] = '{0:.2f}'.format(total_federal_share)
                schedule_page_dict['totallevinShare'] = '{0:.2f}'.format(total_levin_share)
                schedule_page_dict['fedLevinTotalShare'] = total_federal_share+total_levin_share
            schedule_page_dict['committeeName'] = f3x_data['committeeName']
            sh6_outfile = md5_directory + 'SH6/' + line_number + '/page_' + str(page_num) + '.pdf'
            pypdftk.fill_form(sh6_infile, schedule_page_dict, sh6_outfile)
            
            # Memo text changes and build memo pages and return updated current_page_num
            current_page_num = build_memo_page(memo_array,
                                               md5_directory, line_number,
                                               current_page_num, page_num,
                                               total_no_of_pages, sh6_outfile, name='SH6')
    
        pypdftk.concat(directory_files(md5_directory + 'SH6/' + line_number + '/'), md5_directory + 'SH6/' + line_number
                       + '/all_pages.pdf')
        if path.isfile(md5_directory + 'SH6/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SH6/all_pages.pdf', md5_directory + 'SH6/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SH6/temp_all_pages.pdf')
            os.rename(md5_directory + 'SH6/temp_all_pages.pdf', md5_directory + 'SH6/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SH6/' + line_number + '/all_pages.pdf', md5_directory + 'SH6/all_pages.pdf')
    

def build_sh6_line_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, schedule_page_dict,
                                    sh6_schedules, memo_array):
    page_fed_subtotal = 0
    page_levin_subtotal = 0
    if not last_page:
        transactions_in_page = 3

    for index in range(transactions_in_page):
        schedule_dict = sh6_schedules[page_start_index + index]
        process_memo_text(schedule_dict, 'H6', memo_array)
        if schedule_dict['memoCode'] != 'X':
            page_fed_subtotal += schedule_dict['federalShare']
            page_levin_subtotal += schedule_dict['levinShare']
        build_sh_name_date_dict(index + 1, page_start_index, schedule_dict, schedule_page_dict)

    schedule_page_dict['subTotalFederalShare'] = '{0:.2f}'.format(page_fed_subtotal)
    schedule_page_dict['subTotalLevinShare'] = '{0:.2f}'.format(page_levin_subtotal)
    schedule_page_dict['fedLevinSubTotalShare'] = float(schedule_page_dict['subTotalFederalShare'])+float(schedule_page_dict['subTotalLevinShare'])
