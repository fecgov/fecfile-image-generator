"""
Flask settings for fecfile-ImageGenerator project.

"""

import os
import tempfile

# Set the temporary directory
tempfile.tempdir = "temp"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = os.environ.get("DEBUG", True)
ALLOWED_HOSTS = ["*"]


FORM_TEMPLATES_LOCATION = 'templates/forms/{}.pdf'
HTML_FORM_TEMPLATES_LOCATION = 'templates/forms/F99/{}.html'
FORMS_LOCATION = 'templates/forms/{}'
REQUEST_FILE_LOCATION = 'temp/json/{}.json'
# OUTPUT_FILE_LOCATION = 'output/pdf/{}.pdf'
OUTPUT_DIR_LOCATION = "output/pdf/{}/"

# ATTACHMENT_FILE_LOCATION = 'temp/{}.pdf'

# AWS settings

# AWS SES Configuration Settings

# AWS_ACCESS_KEY_ID = os.environ.get('ACCESS_KEY', None)
# AWS_SECRET_ACCESS_KEY = os.environ.get('SECRET_KEY', None)
# AWS_HOST_NAME = 'us-east-1'
# AWS_REGION = 'us-east-1'
AWS_SES_AUTO_THROTTLE = (
    0.5
)  # (default; safety factor applied to rate limit, turn off automatic throttling, set this to None)

# AWS FECFile components bucket name

AWS_FECFILE_OUTPUT_DIRECTORY = os.environ.get('OUTPUT_DIRECTORY', 'output')
AWS_FECFILE_COMPONENTS_BUCKET_NAME = "fecfile-dev-components"
AWS_FECFILE_TEMP_BUCKET_NAME = os.environ.get('TEMP_BUCKET', 'dev-efile-repo')
AWS_FECFILE_PDF_BUCKET_NAME = os.environ.get('PERM_BUCKET', 'fecfile-pdf')


# if False it will create unique file names for every uploaded file
AWS_S3_FILE_OVERWRITE = True
# the url, that your uploaded JSON and print output will be available at
AWS_S3_FECFILE_COMPONENTS_DOMAIN = (
    "%s.s3.amazonaws.com" % AWS_FECFILE_COMPONENTS_BUCKET_NAME
)
# the url, that your uploaded JSON and print output will be available at
AWS_S3_PAGINATION_COMPONENTS_DOMAIN = (
    "%s.s3.amazonaws.com" % AWS_FECFILE_TEMP_BUCKET_NAME
)

S3_FILE_URL = "https://%s/%s/" % (AWS_S3_FECFILE_COMPONENTS_DOMAIN, AWS_FECFILE_OUTPUT_DIRECTORY)

# the sub-directories of temp and output files
# TEMP_FILES_LOCATION = 'temp'
# OUTPUT_FILE_FOLDER = 'output'

# TEMP_FILES_URL = "https://%s/%s/{}" % (AWS_S3_FECFILE_COMPONENTS_DOMAIN, TEMP_FILES_LOCATION)
PRINT_OUTPUT_FILE_URL = "https://%s/%s" % (AWS_S3_FECFILE_COMPONENTS_DOMAIN, OUTPUT_DIR_LOCATION)

FECFILE_UTIL_PRINT_API_URL = os.environ.get('FECFILE_UTIL_URL', 'https://dev-efile-api.efdev.fec.gov/printpdf')
FECFILE_UTIL_API_VERSION = "/v1/fecfileutil"

NXG_FEC_PARSER_API_URL = os.environ.get('PARSER_URL', 'https://dev-efile-api.efdev.fec.gov/receiver')
# NXG_FEC_PARSER_API_URL = os.environ.get('PARSER_URL', 'http://localhost:8090')
NXG_FEC_PARSER_API_VERSION = "/v1"


# SQS Details
DATA_RECEIVER_SQS_QUEUE = os.environ.get('DATA_RECEIVER_SQS_QUEUE', 'datareceiver-dev')
VALIDATION_SQS_QUEUE = os.environ.get('VALIDATION_SQS_QUEUE', 'validator-dev')
IMAGE_NUMBER_SQS_QUEUE = os.environ.get('IMAGE_NUMBER_SQS_QUEUE', 'imaging')
# IMAGE_NUMBER_SQS_QUEUE = os.environ.get('IMAGE_NUMBER_SQS_QUEUE', 'validator-dev')
IMAGE_GENERATOR_SQS_QUEUE = os.environ.get('IMAGE_GENERATOR_SQS_QUEUE', 'imaging-generator')
# Timeout for the message in queue, after the set time interval other process will see it
MESSAGE_VISIBILITY_TIMEOUT = 30  # setting it to 0 for testing