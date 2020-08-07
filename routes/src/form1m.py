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
            
            json_file = request.files.get('json_file')

            # generate md5 for json file
            # FIXME: check if PDF already exist with md5, if exist return pdf instead of re-generating PDF file.
            json_file_md5 = utils.md5_for_file(json_file)
            json_file.stream.seek(0)

            md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
            os.makedirs(md5_directory, exist_ok=True)
            infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F1M')
            # save json file as md5 file name
            json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
            outfile = md5_directory + json_file_md5 + '_temp.pdf'
            # load json file
            f1m_json = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
            # setting timestamp and imgno to empty as these needs to show up after submission
            if stamp_print != 'stamp':
                f1m_json['FILING_TIMESTAMP'] = ''
                f1m_json['IMGNO'] = ''

            # read data from json file
            f1m_data = f1m_json['data']

            # build treasurer name to map it to PDF template
            treasurer_full_name = []
            treasurer_list = ['treasurerLastName', 'treasurerFirstName', 'treasurerMiddleName', 'treasurerPrefix', 'treasurerSuffix']
            for item in treasurer_list:
                if f1m_data[item] not in [None, '', "", " "]:
                    treasurer_full_name.append(f1m_data[item])
            f1m_data['treasurerFullName'] = ", ".join(map(str, treasurer_full_name))
            f1m_data['treasurerName'] = f1m_data['treasurerLastName'] + ", " + f1m_data['treasurerFirstName']
            f1m_data['efStamp'] = '[Electronically Filed]'
            if 'candidates' in f1m_data:
                for candidate in f1m_data['candidates']:
                    candidate_full_name = []
                    list_check = ['candidateLastName', 'candidateFirstName', 'candidateMiddleName', 'candidatePrefix', 'candidateSuffix']
                    for item in list_check:
                        if candidate[item]:
                            candidate_full_name.append(candidate[item])
                    f1m_data['candidateName' + str(candidate['candidateNumber'])] = ", ".join(map(str, candidate_full_name))
                    f1m_data['candidateOffice' + str(candidate['candidateNumber'])] =  candidate['candidateOffice']
                    f1m_data['candidateStateDist' + str(candidate['candidateNumber'])] = "/ ".join(map(str, [candidate['candidateState'], candidate['candidateDistrict']]))
                    f1m_data['contributionDate' + str(candidate['candidateNumber'])] = candidate['contributionDate']

            os.makedirs(md5_directory + str(f1m_data['reportId']) + '/', exist_ok=True)
            infile = current_app.config['FORM_TEMPLATES_LOCATION'].format('F1M')
            print(infile)
            print(f1m_data)
            print(outfile)
            pypdftk.fill_form(infile, f1m_data, outfile)
            shutil.copy(outfile, md5_directory + str(f1m_data['reportId']) + '/F1M.pdf')
            os.remove(outfile)
                
            # push output file to AWSss
            s3 = boto3.client('s3')
            s3.upload_file(md5_directory + str(f1m_data['reportId']) + '/F1M.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
                           md5_directory + 'F1M.pdf',
                           ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
            response = {
                # 'file_name': '{}.pdf'.format(json_file_md5),
                'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5) + 'F1M.pdf'
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