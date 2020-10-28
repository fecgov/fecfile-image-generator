import logging
import flask

from flask import request
from flask_cors import CORS
from routes.src import tmoflask, form99, form1m, form24
from routes.src.f3x import form3x

logger = logging.getLogger()

app = flask.Blueprint("controllers", __name__)
APP = tmoflask.TMOFlask(__name__, instance_relative_config=True)
CORS(app)


@app.route("/print", methods=["POST"])
def print_pdf():
    """
    This function is being invoked from FECFile and Vendors
    HTTP request needs to have form_type, file, and attachment_file
    form_type : F99
    json_file: please refer to below sample JSON
    :return: return JSON response
    sample 1:
    {
    "message": "",
    "results": {
        "pdf_url": "https://fecfile-dev-components.s3.amazonaws.com/output/bd78435a70a70d656145dae89e0e22bb.pdf"
    },
    "success": "true"
    }

    sample 2:
    {
    "message": "",
    "results": {
        "total_pages": 35
    },
    "success": "true"
    }
    """
    form_type = request.form["form_type"]
    if form_type == "F99":
        return form99.print_f99_pdftk_html("")
    elif form_type == "F3X":
        return form3x.print_pdftk("")
    elif form_type == "F1M":
        return form1m.print_pdftk("")
    elif form_type == "F24":
        return form24.print_pdftk("")


@app.route("/paginate", methods=["POST"])
def paginate_pdf():
    """
    This function is being invoked from FECFile and Vendors
    HTTP request needs to have form_type, file, and begin_image_num
    form_type : F99
    json_file: please refer to below sample JSON
    :return: return JSON response
    sample:
    {
    "message": "",
    "results": {
        "total_pages": 35,
        "txn_img_json: {
            "xxx0200804xxxxxxx": 29,
            "xxx0200123xxxxxxx": 4,
        }
    },
    success": "true"
    }
    """
    form_type = request.json["form_type"]
    if form_type == "F99":
        return form99.print_f99_pdftk_html("", paginate=True)
    elif form_type == "F3X":
        return form3x.print_pdftk("", paginate=True)
    elif form_type == "F1M":
        return form1m.paginate()
    elif form_type == "F24":
        return form24.paginate()


@app.route("/stamp_print", methods=["POST"])
def stamp_print_pdf():
    """
    This function is being invoked from FECFile and Vendors
    HTTP request needs to have form_type, file, and attachment_file
    form_type : F99
    json_file: please refer to below sample JSON
    :return: return JSON response
    sample:
    {
    "message": "",
    "results": {
        "pdf_url": "https://fecfile-dev-components.s3.amazonaws.com/output/bd78435a70a70d656145dae89e0e22bb.pdf"
    },
    "success": "true"
    }
    """
    form_type = request.form["form_type"]
    if form_type == "F99":
        return form99.print_f99_pdftk_html("stamp")
