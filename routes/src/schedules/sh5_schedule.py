import os
import pypdftk

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text, build_sh_name_date_dict
from routes.src.utils import directory_files


def print_sh5_line(f3x_data, md5_directory, line_number, sh5_list, page_cnt, start_page,
                    total_no_of_pages):

    if sh5_list:
        last_page_cnt = 2 if len(sh5_list) % 2 == 0 else len(sh5_list) % 2
        current_page_num = start_page + 1
        total_transferred_amt_subtotal = 0
        total_voter_reg_amt_subtotal = 0
        total_voter_id_amt_subtotal = 0
        total_gotv_amt_subtotal = 0
        total_generic_camp_amt_subtotal = 0

        os.makedirs(md5_directory + 'SH5/' + line_number, exist_ok=True)
        sh5_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SH5')

        for sh5_page_no in range(page_cnt):
            current_page_num += sh5_page_no
            page_subtotal = 0
            memo_array = []
            last_page = False
            schedule_page_dict = {}
            schedule_page_dict['lineNumber'] = line_number
            schedule_page_dict['pageNo'] = current_page_num
            schedule_page_dict['totalPages'] = total_no_of_pages
            page_start_index = sh5_page_no * 2
            if sh5_page_no + 1 == page_cnt:
                last_page = True

            # This call prepares data to render on PDF
            build_sh5_per_page_schedule_dict(last_page, last_page_cnt,
                                            page_start_index, schedule_page_dict,
                                            sh5_list, memo_array)

            transferred_amt_subtotal = float(schedule_page_dict['subtotalAmountTransferred'])
            voter_reg_amt_subtotal = float(schedule_page_dict['subvoterRegistrationAmount'])
            voter_id_amt_subtotal = float(schedule_page_dict['subvoterIdAmount'])
            gotv_amt_subtotal = float(schedule_page_dict['subgotvAmount'])
            generic_camp_amt_subtotal = float(schedule_page_dict['subgenericCampaignAmount'])

            total_transferred_amt_subtotal += transferred_amt_subtotal
            total_voter_reg_amt_subtotal += voter_reg_amt_subtotal
            total_voter_id_amt_subtotal += voter_id_amt_subtotal
            total_gotv_amt_subtotal += gotv_amt_subtotal
            total_generic_camp_amt_subtotal += generic_camp_amt_subtotal
            
            if page_cnt == sh5_page_no + 1:
                schedule_page_dict['totalvoterRegistrationAmount'] = '{0:.2f}'.format( total_voter_reg_amt_subtotal)
                schedule_page_dict['totalvoterIdAmount'] = '{0:.2f}'.format(total_voter_id_amt_subtotal)
                schedule_page_dict['totalgotvAmount'] = '{0:.2f}'.format( total_gotv_amt_subtotal)
                schedule_page_dict['totalgenericCampaignAmount'] = '{0:.2f}'.format(total_generic_camp_amt_subtotal)
                schedule_page_dict['totalAmountOfTransfersReceived'] = total_voter_reg_amt_subtotal+total_voter_id_amt_subtotal+total_gotv_amt_subtotal+total_generic_camp_amt_subtotal

            schedule_page_dict['committeeName'] = f3x_data['committeeName']
            sh5_outfile = md5_directory + 'SH5/' + line_number + '/page_' + str(sh5_page_no) + '.pdf'
            pypdftk.fill_form(sh5_infile, schedule_page_dict, sh5_outfile)
            
            # Memo text changes
            memo_dict = {}
            if len(memo_array) >= 1:
                current_page_num += 1
                temp_memo_outfile = md5_directory + 'SH5/' + line_number + '/page_memo_temp.pdf'
                memo_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
                memo_outfile = md5_directory + 'SH5/' + line_number + '/page_memo_' + str(sh5_page_no) + '.pdf'
                memo_dict['scheduleName_1'] = memo_array[0]['scheduleName']
                memo_dict['memoDescription_1'] = memo_array[0]['memoDescription']
                memo_dict['transactionId_1'] = memo_array[0]['transactionId']
                memo_dict['PAGESTR'] = "PAGE " + str(current_page_num) + " / " + str(total_no_of_pages)

                if len(memo_array) >= 2:
                    memo_dict['scheduleName_2'] = memo_array[1]['scheduleName']
                    memo_dict['memoDescription_2'] = memo_array[1]['memoDescription']
                    memo_dict['transactionId_2'] = memo_array[1]['transactionId']
                
                # build page
                pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                pypdftk.concat([sh5_outfile, memo_outfile], temp_memo_outfile)
                os.remove(memo_outfile)
                os.rename(temp_memo_outfile, sh5_outfile)
    
        pypdftk.concat(directory_files(md5_directory + 'SH5/' + line_number + '/'), md5_directory + 'SH5/' + line_number
                       + '/all_pages.pdf')
        if path.isfile(md5_directory + 'SH5/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SH5/all_pages.pdf', md5_directory + 'SH5/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SH5/temp_all_pages.pdf')
            os.rename(md5_directory + 'SH5/temp_all_pages.pdf', md5_directory + 'SH5/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SH5/' + line_number + '/all_pages.pdf', md5_directory + 'SH5/all_pages.pdf')
    

def build_sh5_per_page_schedule_dict(last_page, transactions_in_page, page_start_index, schedule_page_dict,
                                    sh5_schedules, memo_array):
    transferred_amt_subtotal = 0
    voter_reg_amt_subtotal = 0
    voter_id_amt_subtotal = 0
    gotv_amt_subtotal = 0
    generic_camp_amt_subtotal = 0

    if not last_page:
        transactions_in_page = 2

    for index in range(transactions_in_page):
        schedule_dict = sh5_schedules[page_start_index + index]
        process_memo_text(schedule_dict, 'H5', memo_array)
        transferred_amt_subtotal += schedule_dict['totalAmountTransferred']
        voter_reg_amt_subtotal += schedule_dict['voterRegistrationAmount']
        voter_id_amt_subtotal += schedule_dict['voterIdAmount']
        gotv_amt_subtotal += schedule_dict['gotvAmount']
        generic_camp_amt_subtotal += schedule_dict['genericCampaignAmount']
        build_sh_name_date_dict(index + 1, page_start_index, schedule_dict, schedule_page_dict)

    schedule_page_dict['subtotalAmountTransferred'] = '{0:.2f}'.format(transferred_amt_subtotal)
    schedule_page_dict['subvoterRegistrationAmount'] = '{0:.2f}'.format( voter_reg_amt_subtotal)
    schedule_page_dict['subvoterIdAmount'] = '{0:.2f}'.format(voter_id_amt_subtotal)
    schedule_page_dict['subgotvAmount'] = '{0:.2f}'.format( gotv_amt_subtotal)
    schedule_page_dict['subgenericCampaignAmount'] = '{0:.2f}'.format(generic_camp_amt_subtotal)

    # schedule_page_dict['subTotalFedNonFedShare'] = float(schedule_page_dict['subFedShare'])+float(schedule_page_dict['subNonFedShare'])

