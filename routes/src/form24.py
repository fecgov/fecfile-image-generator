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
	# try:
		if 'json_file' in request.files:
			json_file = request.files.get('json_file')

			# generate md5 for json file
			# FIXME: check if PDF already exist with md5, if exist return pdf instead of re-generating PDF file.
			json_file_md5 = utils.md5_for_file(json_file)
			json_file.stream.seek(0)

			md5_directory = current_app.config['OUTPUT_DIR_LOCATION'].format(json_file_md5)
			os.makedirs(md5_directory, exist_ok=True)
			# save json file as md5 file name
			json_file.save(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5))
			# load json file
			f24_json = json.load(open(current_app.config['REQUEST_FILE_LOCATION'].format(json_file_md5)))
			# setting timestamp and imgno to empty as these needs to show up after submission
			output = {}
			if stamp_print != 'stamp':
				output['FILING_TIMESTAMP'] = ''
				output['IMGNO'] = ''

			# read data from json file
			f24_data = f24_json['data']
			reportId = str(f24_data['reportId'])
			os.makedirs(md5_directory + reportId + '/', exist_ok=True)
			output['committeeId'] = f24_data['committeeId']
			output['committeeName'] = f24_data['committeeName']
			output['reportType'] = f24_data['reportType']
			output['amendIndicator'] = f24_data['amendIndicator']

			# checking report memo text
			report_memo_flag = True if f24_data.get('memoText') else False

			# build treasurer name to map it to PDF template
			treasurer_list = ['treasurerLastName', 'treasurerFirstName', 'treasurerMiddleName', 'treasurerPrefix', 'treasurerSuffix']
			output['treasurerFullName'] = ""
			for item in treasurer_list:
				output['treasurerFullName'] += f24_data.get(item, "")+','
			output['treasurerName'] = f24_data['treasurerLastName'] + ", " + f24_data['treasurerFirstName']
			output['efStamp'] = '[Electronically Filed]'
			if output['amendIndicator'] == 'A':
				if f24_data['amendDate']:
					amend_date_array = f24_data['amendDate'].split("/")
					output['amendDate_MM'] = amend_date_array[0]
					output['amendDate_DD'] = amend_date_array[1]
					output['amendDate_YY'] = amend_date_array[2]

			# Calculating total number of pages
			if not f24_data['schedules'].get('SE'):
				output['PAGENO'] = page_index
				output['TOTALPAGES'] = page_index
			else:
				if len(f24_data['schedules']['SE']) % 2 == 0:
					output['TOTALPAGES'] = len(f24_data['schedules']['SE'])//2
				else:
					output['TOTALPAGES'] = (len(f24_data['schedules']['SE'])//2)+1
				full_counter = 0
				for page in range(0, output['TOTALPAGES'], 1):
					counter = 0
					for i in range(0,2,1):
						if 2*(page)+i < len(f24_data['schedules']['SE']):
							item = f24_data['schedules'].get('SE')[2*(page)+i]
							if item.get("memoCode") == 'X' and item.get("memoDescription"):
								counter = 1
					full_counter = full_counter + counter
				if report_memo_flag: full_counter += 1
				output['TOTALPAGES'] += full_counter

			# Printing report memo text page
			if report_memo_flag:
				memo_dict = {'scheduleName_1' : 'F3X' + f24_data['amendIndicator'],
							'memoDescription_1' : f24_data['memoText'],
							'PAGESTR' : "PAGE " + str(1) + " / " + str(output['TOTALPAGES'])}
				print_summ(memo_dict, 1, reportId, json_file_md5)

			if f24_data.get('filedDate'):
				filed_date_array = f24_data['filedDate'].split("/")
				output['filedDate_MM'] = filed_date_array[0]
				output['filedDate_DD'] = filed_date_array[1]
				output['filedDate_YY'] = filed_date_array[2]
			if f24_data['schedules'].get('SE'):
				page_index = 2 if report_memo_flag else 1
				page_dict = {}
				sub_total = 0
				total = 0
				for i, se in enumerate(f24_data['schedules']['SE']):
					index = (i%2)+1
					if 'payeeLastName' in se and se['payeeLastName']:
						page_dict["payeeName_" + str(index)] = ""
						for item in ['payeeLastName', 'payeeFirstName', 'payeeMiddleName', 'payeePrefix', 'payeeSuffix']:
							page_dict["payeeName_" + str(index)] += se.get(item,"")+','

					elif 'payeeOrganizationName' in se:
						page_dict["payeeName_" + str(index)] = se['payeeOrganizationName']
					page_dict["memoCode_" + str(index)] = se['memoCode']
					page_dict["memoDescription_" + str(index)] = se['memoDescription']
					page_dict["payeeStreet1_" + str(index)] = se['payeeStreet1']
					page_dict["payeeStreet2_" + str(index)] = se['payeeStreet2']
					page_dict["payeeCity_" + str(index)] = se['payeeCity']
					page_dict["payeeState_" + str(index)] = se['payeeState']
					page_dict["payeeZipCode_" + str(index)] = se['payeeZipCode']
					page_dict["expenditureAmount_" + str(index)] = "{:.2f}".format(se['expenditureAmount'])
					page_dict["transactionId_" + str(index)] = se['transactionId']
					page_dict["expenditurePurpose_" + str(index)] = se['expenditurePurposeDescription']
					page_dict["supportOppose_" + str(index)] = se['support/opposeCode']
					page_dict["candidateOffice_" + str(index)] = se['candidateOffice']
					page_dict["candidateState_" + str(index)] = se['candidateState']
					page_dict["candidateDistrict_" + str(index)] = se['candidateDistrict']
					page_dict["electionType_" + str(index)] = se['electionCode'][:1]
					page_dict["electionYear_" + str(index)] = se['electionCode'][1:]
					page_dict["electionOtherDescription_" + str(index)] = se['electionOtherDescription']
					page_dict["calendarYTD_" + str(index)] = "{:.2f}".format(se['calendarYTDPerElectionForOffice'])
					if se['disseminationDate']:
						dissem_date_array = se['disseminationDate'].split("/")
						page_dict["disseminationDate_MM_" + str(index)] = dissem_date_array[0]
						page_dict["disseminationDate_DD_" + str(index)] = dissem_date_array[1]
						page_dict["disseminationDate_YY_" + str(index)] = dissem_date_array[2]
					if se['disbursementDate']:
						disburse_date_array = se['disbursementDate'].split("/")
						page_dict["disbursementDate_MM_" + str(index)] = disburse_date_array[0]
						page_dict["disbursementDate_DD_" + str(index)] = disburse_date_array[1]
						page_dict["disbursementDate_YY_" + str(index)] = disburse_date_array[2]
					page_dict["candidateName_" + str(index)] = ""
					for item in ['candidateLastName', 'candidateFirstName', 'candidateMiddleName', 'candidatePrefix', 'candidateSuffix']:
						page_dict["candidateName_" + str(index)] += se.get(item,"")+','
					# 	if se[item]: candidate_name_list.append(se[item])
					# page_dict["candidateName_" + str(index)] = " ".join(candidate_name_list)
					if se.get('memoCode') != 'X':
						sub_total += se['expenditureAmount']
						total += se['expenditureAmount']
					# print and reset
					if (index%2 == 0 or i == (len(f24_data['schedules']['SE'])-1)):
						page_dict['PAGENO'] = page_index
						page_dict["subTotal"] = "{:.2f}".format(sub_total)
						if i == (len(f24_data['schedules']['SE'])-1): page_dict["total"] = "{:.2f}".format(total)
						print_dict = {**output, **page_dict}
						print_f24(print_dict, page_index, reportId, json_file_md5)
						page_index += 1
						memo_dict = {}
						for xir in range(1, 3):
							if page_dict.get("memoCode_{}".format(xir)) == 'X' and page_dict.get("memoDescription_{}".format(xir)):
								memo_dict["scheduleName_{}".format(xir)] = 'SE'
								memo_dict["memoDescription_{}".format(xir)] = page_dict["memoDescription_{}".format(xir)]
								memo_dict["transactionId_{}".format(xir)] = page_dict["transactionId_{}".format(xir)]
								memo_dict['PAGESTR'] = "PAGE " + str(page_index) + " / " + str(output['TOTALPAGES'])
						if memo_dict:
							print_summ(memo_dict, page_index, reportId, json_file_md5)
							page_index += 1
						page_dict = {}
						sub_total = 0
			else:
				output["subTotal"] = "0.00"
				output["total"] = "0.00"
				print_f24(output, 1, reportId, json_file_md5)

			# Concatinating all pages generated
			for i in range(1, output['TOTALPAGES']+1, 1):
				if path.isfile(md5_directory + reportId + '/F24_temp.pdf'):
					pypdftk.concat([md5_directory + reportId + '/F24_temp.pdf', md5_directory + reportId + '/F24_{}.pdf'.format(i)],
					md5_directory + reportId + '/concat_F24.pdf')
					os.rename(md5_directory + reportId + '/concat_F24.pdf', md5_directory + reportId + '/F24_temp.pdf')
					os.remove(md5_directory + reportId + '/F24_{}.pdf'.format(i))
				else:
					os.rename(md5_directory + reportId + '/F24_{}.pdf'.format(i), md5_directory + reportId + '/F24_temp.pdf')
			os.rename(md5_directory + reportId + '/F24_temp.pdf', md5_directory + reportId + '/F24.pdf')

			# push output file to AWS
			s3 = boto3.client('s3')
			s3.upload_file(md5_directory + reportId + '/F24.pdf', current_app.config['AWS_FECFILE_COMPONENTS_BUCKET_NAME'],
			md5_directory + 'F24.pdf',
			ExtraArgs={'ContentType': "application/pdf", 'ACL': "public-read"})
			response = {
			'pdf_url': current_app.config['PRINT_OUTPUT_FILE_URL'].format(json_file_md5) + 'F24.pdf'
			}
			# response = {'yes':True}
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
	# except Exception as e:
	# 	return error('Error generating print preview, error message: ' + str(e))

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