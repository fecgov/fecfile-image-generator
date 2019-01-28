import flask


class TMOResponse(flask.Response):
    default_mimetype = "application/json"


class TMOFlask(flask.Flask):
    response_class = TMOResponse
