"""
Flask settings for fecfile-ImageGenerator project.

"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = os.environ.get('DEBUG', True)
ALLOWED_HOSTS = ['*']

FORM_TEMPLATES_LOCATION = 'templates/forms/{}.pdf'
REQUEST_FILE_LOCATION = 'temp/json/{}.json'
OUTPUT_FILE_LOCATION = 'output/pdf/{}.pdf'
# ATTACHMENT_FILE_LOCATION = 'temp/{}.pdf'

# AWS settings

# AWS SES Configuration Settings

# AWS_ACCESS_KEY_ID = os.environ.get('ACCESS_KEY', None)
# AWS_SECRET_ACCESS_KEY = os.environ.get('SECRET_KEY', None)
# AWS_HOST_NAME = 'us-east-1'
# AWS_REGION = 'us-east-1'
AWS_SES_AUTO_THROTTLE = 0.5 # (default; safety factor applied to rate limit, turn off automatic throttling, set this to None)

# AWS FECFile components bucket name
AWS_FECFILE_COMPONENTS_BUCKET_NAME = 'fecfile-dev-components'

# if False it will create unique file names for every uploaded file
AWS_S3_FILE_OVERWRITE = True
# the url, that your uploaded JSON and print output will be available at
AWS_S3_FECFILE_COMPONENTS_DOMAIN = '%s.s3.amazonaws.com' % AWS_FECFILE_COMPONENTS_BUCKET_NAME

# the sub-directories of temp and output files
# TEMP_FILES_LOCATION = 'temp'
# OUTPUT_FILE_FOLDER = 'output'

# TEMP_FILES_URL = "https://%s/%s/{}" % (AWS_S3_FECFILE_COMPONENTS_DOMAIN, TEMP_FILES_LOCATION)
PRINT_OUTPUT_FILE_URL = "https://%s/%s" % (AWS_S3_FECFILE_COMPONENTS_DOMAIN, OUTPUT_FILE_LOCATION)






