import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path


def print_sd_line(f3x_data, md5_directory, sd_dict, sd_start_page, total_no_of_pages, total_sd_pages, totalOutstandingLoans):
    sd_total_balance = '0.00'
    sd_schedule_total = 0
    page_count = 0
    os.makedirs(md5_directory + 'SD/', exist_ok=True)
    sd_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SD')
    try:
        for line_number in sd_dict:
            sd_list = sd_dict.get(line_number)
            sd_sub_total = 0
            sd_page_dict = {}
            sd_page_dict['committeeName'] = f3x_data.get('committeeName')
            sd_page_dict['totalNoPages'] = total_no_of_pages
            sd_page_dict['lineNumber'] = line_number

            for index in range(len(sd_list)):
                sd_schedule_total += float(sd_list[index].get('balanceAtClose'))
                sd_sub_total += float(sd_list[index].get('balanceAtClose'))
                sd_page_dict['pageNo'] = sd_start_page + page_count
                concat_no = index % 3 + 1

                if 'creditorOrganizationName' in sd_list[index] and sd_list[index].get('creditorOrganizationName') != "":
                    sd_page_dict['creditorName_{}'.format(concat_no)] = sd_list[index].get('creditorOrganizationName')
                else:
                    sd_page_dict['creditorName_{}'.format(concat_no)] = ""
                    for item in ['creditorPrefix', 'creditorLastName', 'creditorFirstName', 'creditorMiddleName', 'creditorSuffix']:
                        if sd_list[index].get(item) != "":
                            sd_page_dict['creditorName_{}'.format(concat_no)] += sd_list[index].get(item) + " "
                
                for item in ['creditorStreet1', 'creditorStreet2', 'creditorCity', 'creditorState', 'creditorZipCode', 'purposeOfDebtOrObligation', 'transactionId']:
                    sd_page_dict[item+'_{}'.format(concat_no)] = sd_list[index].get(item)
                
                for item in ['beginningBalance', 'incurredAmount', 'paymentAmount', 'balanceAtClose']:
                    sd_page_dict[item+'_{}'.format(concat_no)] = '{0:.2f}'.format(float(sd_list[index].get(item)))
                
                if index % 3 == 2 or index == len(sd_list) - 1:
                    sd_page_dict['subTotal'] = '{0:.2f}'.format(sd_sub_total)
                    if page_count == total_sd_pages - 1:
                        sd_page_dict['total'] = '{0:.2f}'.format(sd_schedule_total)
                        sd_page_dict['totalOutstandingLoans'] = totalOutstandingLoans
                        sd_total_balance = sd_page_dict['totalBalance'] = '{0:.2f}'.format(sd_schedule_total + float(totalOutstandingLoans))
                    sd_outfile = md5_directory + 'SD' + '/page_' + str(sd_page_dict['pageNo']) + '.pdf'
                    pypdftk.fill_form(sd_infile, sd_page_dict, sd_outfile)
                    del_j = 1
                    
                    while del_j <= index % 3 + 1:
                        for item in ['creditorName', 'creditorStreet1', 'creditorStreet2', 'creditorCity', 'creditorState', 'creditorZipCode', 
                            'purposeOfDebtOrObligation', 'transactionId','beginningBalance', 'incurredAmount', 'paymentAmount', 'balanceAtClose']:
                            del sd_page_dict[item+'_{}'.format(del_j)]
                        del_j += 1
                    if path.isfile(md5_directory + 'SD/all_pages.pdf'):
                        pypdftk.concat([md5_directory + 'SD/all_pages.pdf', md5_directory + 'SD' + '/page_' + str(sd_page_dict['pageNo']) + '.pdf'],
                                        md5_directory + 'SD/temp_all_pages.pdf')
                        os.rename(md5_directory + 'SD/temp_all_pages.pdf', md5_directory + 'SD/all_pages.pdf')
                    else:
                        os.rename(md5_directory + 'SD' + '/page_' + str(sd_page_dict['pageNo']) + '.pdf', md5_directory + 'SD/all_pages.pdf')
                    page_count += 1
                    sd_sub_total = 0
        return sd_total_balance
    except:
        traceback.print_exception(*sys.exc_info())
