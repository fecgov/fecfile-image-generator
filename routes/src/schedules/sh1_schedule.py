import os
import pypdftk

from flask import current_app
from os import path
from routes.src.utils import directory_files


def print_sh1_line(f3x_data, md5_directory, tran_type_ident, sh_h1, sh1_page_cnt, sh1_start_page,
                     total_no_of_pages):

    # presidentialOnly = presidentialAndSenate = senateOnly = nonPresidentialAndNonSenate = False
    try:
        os.makedirs(md5_directory + 'SH1/' + tran_type_ident, exist_ok=True)
        sh1_infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('SH1')
        sh1_page_no = 1
        if sh1_page_cnt > 0:
            sh1_schedule_page_dict = {}
            # sh1_schedule_page_dict['pageNo'] = sh1_start_page + 1
            sh1_schedule_page_dict['PAGESTR'] = "PAGE " + str(sh1_start_page + 1) + " / " + str(total_no_of_pages)
            # sh1_schedule_page_dict['totalPages'] = total_no_of_pages
            for sh1_line in sh_h1:
                presidentialOnly = sh1_line['presidentialOnly']
                presidentialAndSenate = sh1_line['presidentialAndSenate']
                senateOnly = sh1_line['senateOnly']
                nonPresidentialAndNonSenate = sh1_line['nonPresidentialAndNonSenate']
                if presidentialOnly or presidentialAndSenate or senateOnly or nonPresidentialAndNonSenate:
                    sh1_schedule_page_dict['presidentialOnly'] = str(sh1_line['presidentialOnly'])
                    sh1_schedule_page_dict['presidentialAndSenate'] = str(sh1_line['presidentialAndSenate'])
                    sh1_schedule_page_dict['senateOnly'] = str(sh1_line['senateOnly'])
                    sh1_schedule_page_dict['nonPresidentialAndNonSenate'] = str(sh1_line['nonPresidentialAndNonSenate'])
                else:
                    sh1_schedule_page_dict['federalPercent'] = '{0:.2f}'.format(float(sh1_line['federalPercent']))
                    sh1_schedule_page_dict['nonFederalPercent'] = '{0:.2f}'.format(float(sh1_line['nonFederalPercent']))
                    sh1_schedule_page_dict['administrative'] = str(sh1_line['administrative'])
                    sh1_schedule_page_dict['genericVoterDrive'] = str(sh1_line['genericVoterDrive'])
                    sh1_schedule_page_dict['publicCommunications'] = str(sh1_line['publicCommunications'])
                
                sh1_schedule_page_dict['committeeName'] = f3x_data['committeeName']
                sh1_outfile = md5_directory + 'SH1/' + tran_type_ident + '/page_' + str(sh1_page_no) + '.pdf'
                
                pypdftk.fill_form(sh1_infile, sh1_schedule_page_dict, sh1_outfile)
                sh1_page_no += 1

        pypdftk.concat(directory_files(md5_directory + 'SH1/' + tran_type_ident + '/'), md5_directory + 'SH1/' + tran_type_ident
                       + '/all_pages.pdf')
        if path.isfile(md5_directory + 'SH1/all_pages.pdf'):
            pypdftk.concat([md5_directory + 'SH1/all_pages.pdf', md5_directory + 'SH1/' + tran_type_ident + '/all_pages.pdf'],
                           md5_directory + 'SH1/temp_all_pages.pdf')
            os.rename(md5_directory + 'SH1/temp_all_pages.pdf', md5_directory + 'SH1/all_pages.pdf')
        else:
            os.rename(md5_directory + 'SH1/' + tran_type_ident + '/all_pages.pdf', md5_directory + 'SH1/all_pages.pdf')
    except Exception as e:
        raise e

