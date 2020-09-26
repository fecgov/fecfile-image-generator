import os
import pypdftk

from flask import current_app
from os import path
from routes.src.f3x.helper import process_memo_text, build_memo_page
from routes.src.utils import directory_files

def print_sa_line(f3x_data, md5_directory, line_number, sa_list, page_cnt, start_page,
                    total_no_of_pages):

    if sa_list:
        last_page_cnt = 3 if len(sa_list) % 3 == 0 else len(sa_list) % 3
        current_page_num = start_page + 1
        schedule_total = 0
        os.makedirs(md5_directory + 'SA/' + line_number, exist_ok=True)
        sa_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SA')

        for page_num in range(page_cnt):
            current_page_num += page_num
            page_subtotal = 0
            memo_array = []
            last_page = False
            schedule_page_dict = {}
            schedule_page_dict['lineNumber'] = line_number
            schedule_page_dict['pageNo'] = current_page_num
            schedule_page_dict['totalPages'] = total_no_of_pages
            start_index = page_num * 3
            if page_num + 1 == page_cnt:
                last_page = True
            
            # This call prepares data to render on PDF
            build_sa_per_page_schedule_dict(last_page,
                                            last_page_cnt,
                                            start_index,
                                            schedule_page_dict,
                                            sa_list, memo_array)
            
            page_subtotal = float(schedule_page_dict['pageSubtotal'])
            schedule_total += page_subtotal

            if page_cnt == page_num + 1:
                schedule_page_dict['scheduleTotal'] = '{0:.2f}'.format(schedule_total)

            schedule_page_dict['committeeName'] = f3x_data['committeeName']
            sa_outfile = md5_directory + 'SA/' + line_number + '/page_' + str(page_num) + '.pdf'
            pypdftk.fill_form(sa_infile, schedule_page_dict, sa_outfile)
            
            # Memo text changes and build memo pages and return updated current_page_num
            current_page_num = build_memo_page(memo_array, 
                                               md5_directory, line_number, 
                                               current_page_num, page_num, 
                                               total_no_of_pages, sa_outfile, name='SA')
            

        pypdftk.concat(directory_files(md5_directory + 'SA/' + line_number + '/'), md5_directory + 'SA/' + line_number
                       + '/all_pages.pdf')

        if path.isfile(md5_directory + 'SA/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SA/all_pages.pdf', md5_directory + 'SA/' + line_number + '/all_pages.pdf'],
                           md5_directory + 'SA/temp_all_pages.pdf')
            os.rename(md5_directory + 'SA/temp_all_pages.pdf', md5_directory + 'SA/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SA/' + line_number + '/all_pages.pdf', md5_directory + 'SA/all_pages.pdf')

        # handling page number and returning current_page_num to keep track
        return current_page_num
    else:
        # handling page number and returning start page as no data is present
        return start_page

def build_sa_per_page_schedule_dict(last_page, transactions_in_page, start_index, schedule_page_dict,
                                    schedules, memo_array):
    page_subtotal = 0
    if not last_page:
        transactions_in_page = 3
    
    for index in range(transactions_in_page):
        schedule_dict = schedules[start_index + index]
        process_memo_text(schedule_dict, 'SA', memo_array)
        if schedule_dict['memoCode'] != 'X':
            page_subtotal += schedule_dict['contributionAmount']
        build_contributor_name_date_dict(index + 1, start_index, schedule_dict, schedule_page_dict)
    
    schedule_page_dict['pageSubtotal'] = '{0:.2f}'.format(page_subtotal)


def build_contributor_name_date_dict(index, key, schedule_dict, schedule_page_dict):
    try:
        if schedule_dict.get('contributorLastName'):
            contributor_full_name = []
            contributor_full_name.append(schedule_dict.get('contributorLastName'))
            contributor_full_name.append(schedule_dict.get('contributorFirstName'))
            contributor_full_name.append(schedule_dict.get('contributorMiddleName'))
            contributor_full_name.append(schedule_dict.get('contributorPrefix'))
            contributor_full_name.append(schedule_dict.get('contributorSuffix'))

	        # removing empty string from contributor_full_name if any
            contributor_full_name = list(filter(None, contributor_full_name))
            schedule_page_dict["contributorName_" + str(index)] = ",".join(map(str, contributor_full_name))
            
            del schedule_dict['contributorLastName']
            del schedule_dict['contributorFirstName']
            del schedule_dict['contributorMiddleName']
            del schedule_dict['contributorPrefix']
            del schedule_dict['contributorSuffix']
            
        elif 'contributorOrgName' in schedule_dict:
            schedule_page_dict["contributorName_" + str(index)] = schedule_dict['contributorOrgName']
            del schedule_dict['contributorOrgName']

        if 'electionCode' in schedule_dict and schedule_dict['electionCode']:
            key = 'electionCode'
            if schedule_dict[key][0] in ['P', 'G']:
                schedule_dict['electionType'] = schedule_dict[key][0:1]
            else:
                schedule_dict['electionType'] = 'O'
            schedule_dict['electionYear'] = schedule_dict[key][1::]

        if 'contributionDate' in schedule_dict:
            date_array = schedule_dict['contributionDate'].split("/")
            schedule_page_dict['contributionDateMonth_' + str(index)] = date_array[0]
            schedule_page_dict['contributionDateDay_' + str(index)] = date_array[1]
            schedule_page_dict['contributionDateYear_' + str(index)] = date_array[2]
            del schedule_dict['contributionDate']

        if 'contributionAmount' in schedule_dict:
            if schedule_dict['contributionAmount'] == '':
                schedule_dict['contributionAmount'] = 0.0
            schedule_page_dict['contributionAmount_' + str(index)] = '{0:.2f}'.format(
                schedule_dict['contributionAmount'])
            del schedule_dict['contributionAmount']

        if 'contributionAggregate' in schedule_dict:
            if schedule_dict['contributionAggregate'] == '':
                schedule_dict['contributionAggregate'] = 0.0
            schedule_page_dict['contributionAggregate_' + str(index)] = '{0:.2f}'.format(
                schedule_dict['contributionAggregate'])
            del schedule_dict['contributionAggregate']

        for key in schedule_dict:
            if key != 'lineNumber':
                schedule_page_dict[key + '_' + str(index)] = schedule_dict[key]
    except Exception as e:
        print('Error at key: ' + key + ' in Schedule A transaction: ' + str(schedule_dict))
        raise e
