import math
import os
import pypdftk

from flask import current_app


def process_memo_text(schedule_dict, schedule, memo_array):
    if schedule_dict.get('memoDescription'):
        memo_array.append(
            {'scheduleName': schedule + schedule_dict['lineNumber'],
             'memoDescription': schedule_dict['memoDescription'],
             'transactionId': schedule_dict['transactionId']})


def build_sh_name_date_dict(index, key, sh_schedule_dict, sh_schedule_page_dict):
    try:
        float_val = ('federalShare','levinShare','totalFedLevinAmount','nonfederalShare', 'totalFedNonfedAmount', 
                     'totalAmountTransferred','voterRegistrationAmount','voterIdAmount', 'gotvAmount', 
                     'genericCampaignAmount','activityEventTotalYTD')

        if 'activityEventType' in sh_schedule_dict:
            sh_schedule_page_dict["activityEventType_" + str(index)] = sh_schedule_dict['activityEventType']

        if 'payeeLastName' in sh_schedule_dict and sh_schedule_dict['payeeLastName']:
            sh_schedule_page_dict['payeeName_' + str(index)] = (sh_schedule_dict['payeeLastName'] + ','
                                                                      + sh_schedule_dict['payeeFirstName'] + ','
                                                                      + sh_schedule_dict['payeeMiddleName'] + ','
                                                                      + sh_schedule_dict['payeePrefix'] + ','
                                                                      + sh_schedule_dict['payeeSuffix'])
        elif 'payeeOrganizationName' in sh_schedule_dict:
            sh_schedule_page_dict["payeeName_" + str(index)] = sh_schedule_dict['payeeOrganizationName']


        for key in sh_schedule_dict:
            if key == 'expenditureDate':
                date_array = sh_schedule_dict[key].split("/")
                sh_schedule_page_dict['expenditureDateMonth_' + str(index)] = date_array[0]
                sh_schedule_page_dict['expenditureDateDay_' + str(index)] = date_array[1]
                sh_schedule_page_dict['expenditureDateYear_' + str(index)] = date_array[2]

            if key == 'receiptDate':
                
                date_array = sh_schedule_dict[key].split("/")
                sh_schedule_page_dict['receiptDateMonth_' + str(index)] = date_array[0]
                sh_schedule_page_dict['receiptDateDay_' + str(index)] = date_array[1]
                sh_schedule_page_dict['receiptDateYear_' + str(index)] = date_array[2]

            if key in float_val:
                sh_schedule_page_dict[key + '_' + str(index)] = '{:.2f}'.format(float(sh_schedule_dict[key]))
                continue
            else:
                if key != 0:
                    sh_schedule_page_dict[key + '_' + str(index)] = sh_schedule_dict[key]

            if key != 'lineNumber' and key != 0:
                sh_schedule_page_dict[key + '_' + str(index)] = sh_schedule_dict[key]            

    except Exception as e:
        print('Error at key: ' + key + ' in Schedule SH transaction: ' + str(sh_schedule_dict))
        raise e


def calculate_page_count(schedules, num):

    sch_count = memo_sch_count = 0
    sch_page_count = memo_sch_page_count = 0

    for schedule in schedules:
        sch_count += 1
        if schedule.get("memoDescription"):
            memo_sch_count += 1

        if sch_count == num:
            sch_page_count += 1
            memo_sch_page_count += math.ceil(memo_sch_count / 2)
            sch_count = 0
            memo_sch_count = 0

    if sch_count:
        sch_page_count += 1

    if memo_sch_count:
        memo_sch_page_count += 1

    return sch_page_count, memo_sch_page_count

               
def build_memo_page(memo_array, md5_directory, line_number, current_page_num, page_num, total_no_of_pages, outfile, name):
    memo_dict = {}
    if len(memo_array) >= 1:
        current_page_num += 1
        temp_memo_outfile = md5_directory + name + '/' + line_number + '/page_memo_temp.pdf'
        memo_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('TEXT')
        memo_outfile = md5_directory + name + '/' + line_number + '/page_memo_' + str(page_num) + '.pdf'
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
        pypdftk.concat([outfile, memo_outfile], temp_memo_outfile)
        os.remove(memo_outfile)
        os.rename(temp_memo_outfile, outfile)

        if len(memo_array) >= 3:
            current_page_num += 1
            memo_dict = {}
            memo_outfile = md5_directory + name + '/' + line_number + '/page_memo_' + str(page_num) + '.pdf'
            memo_dict['scheduleName_1'] = memo_array[2]['scheduleName']
            memo_dict['memoDescription_1'] = memo_array[2]['memoDescription']
            memo_dict['transactionId_1'] = memo_array[2]['transactionId']
            memo_dict['PAGESTR']="PAGE " + str(current_page_num) + " / " + str(total_no_of_pages)
            pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
            pypdftk.concat([outfile, memo_outfile], temp_memo_outfile)
            os.remove(memo_outfile)
            os.rename(temp_memo_outfile, outfile)
            
    return current_page_num
