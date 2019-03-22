import logging
import flask
import flask_cors

from routes.src import common
from routes.src import log
from routes.src import controllers
from routes.src import tmoflask

APP = tmoflask.TMOFlask(__name__)
flask_cors.CORS(APP)

LOGGER = logging.getLogger()
log.log_init()


@APP.errorhandler(ValueError)
def handle_valueerror_exception(error):
    """
    Flask Error Handler for ValueError
    :param str error: error message
    :return: tuple(return envelope string, http status code int)
    :rtype: tuple(str, int)
    """
    envelope = common.get_return_envelope(success="false", message=str(error))
    LOGGER.exception(str(error))
    return flask.jsonify(**envelope), 400


@APP.errorhandler(Exception)
def handle_general_exception(error):
    """
    Flask Error Handler for Exception
    :param str error:  error message
    :return: tuple(return envelope string, http status code int)
    :rtype: tuple(str, int)
    """
    envelope = common.get_return_envelope(success="false", message=str(error))
    LOGGER.exception(str(error))
    return flask.jsonify(**envelope), 500


APP.register_blueprint(controllers.app, url_prefix="/v1")

APP.config.from_object("config")
# APP.config.from_pyfile('config.py', silent=True)
