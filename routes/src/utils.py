import hashlib
import os
import flask


from shutil import rmtree
from flask_api import status
from routes.src import common


def md5_for_file(f, block_size=4096):
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()


def md5_for_text(text):
    result = hashlib.md5(text.encode())
    return result.hexdigest()


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
        envelope = common.get_return_envelope("false", msg)
        status_code = status.HTTP_400_BAD_REQUEST
        return flask.jsonify(**envelope), status_code


# delete directory if it exists
def delete_directory(dir_name):
    if os.path.isdir(dir_name) and os.listdir(dir_name):
        rmtree(dir_name)
