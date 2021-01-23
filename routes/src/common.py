"""
    This module handles common functions
"""

import datetime
import json
import logging

import flask

LOGGER = logging.getLogger()


def get_return_envelope(success=True, message="", data=None):
    """
    Builds and returns a 'return envelope'
    :param str success: Should be 'true' or 'false'
    :param str message: String you want returned to api caller
    :param data: Can be any data structure you want returned to api caller.
    :return: return envelope
    :rtype: dict
    """
    if not data:
        data = {}
    envelope = {"success": success, "message": message, "results": data}
    return envelope


def check_response_and_return_or_log(response, url):
    """
    Checks for response status_code and text and returns
    either tuple or None. This common method can be used
    when intending to log error in cases of response
    status code greater than 400 and if there is failure
    in communication when status code is less than 400.

    :param response: response received in the communication process
    :param url: url attempted to communicate
    :return: return success indication from response, response text
    :rtype: tuple if response.status_code < 400 else None
    """
    if response.status_code < 400:
        if response.text:
            try:
                response_text = json.loads(response.text)
                if response_text.get("success").lower() == "false":
                    return False, response_text.get("data")
                else:
                    return True, response_text.get("data")
            except Exception as e:
                LOGGER.error(
                    u'Exception "%s" raised when trying to read '
                    u"response.text as json" % str(e)
                )
                # if response.text does not indicate failure assume
                # success = True
                return True, response.text
        else:
            # if response.text does not indicate failure assume success = True
            return True, None

    elif 400 <= response.status_code < 500:
        LOGGER.error(
            u"%s Bouncer Service Error: %s for url: %s"
            % (response.status_code, response.text, url)
        )

    elif 500 <= response.status_code < 600:
        LOGGER.error(
            u"%s Server Error: %s for url: %s"
            % (response.status_code, response.text, url)
        )


def get_post_data(required_fields, non_required_fields=None):
    """
    Standardizes the way post data is retrieved from request object.
    Any post data that is not included in the required_fields list or
    non_required_fields list will not be returned.
    :param list required_fields: Required fields that should be pulled
                                 from post data
    :param list non_required_fields: Non-required fields that should be
                                     pulled from post data
    :return:  dictionary of post data
    :rtype:  dict
    :raises ValueError:
    """
    if not non_required_fields:
        non_required_fields = []
    data = flask.request.get_json()
    if not data:
        raise ValueError("This requires a 'Content-Type: application/json header.")

    missing_fields = []
    fields = {}
    for field in required_fields:
        field = field.lower()
        if field not in data:
            missing_fields.append(field)
            continue

        fields[field] = data[field]

    for field in non_required_fields:
        field = field.lower()
        if field in data:
            fields[field] = data[field]

    if len(missing_fields):
        raise ValueError(
            "Missing required fields '%s' in POST JSON data." % str(missing_fields)
        )

    return fields


def get_current_datetime():
    """
    Returns a string of the current date/time
    :return: current date/time
    :rtype: str
    """
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
