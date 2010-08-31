import httplib
import logging
import sys
import traceback

from google.appengine.ext import webapp

from pushmaster.log import ClassLogger

class HTTPStatusCode(Exception):
    def __init__(self, code, message=None):
        message = message or httplib.responses.get(code, 'Unknown Error')
        self.code = code
        super(HTTPStatusCode, self).__init__(message)

class RequestHandler(webapp.RequestHandler):
    log = ClassLogger()

    @property
    def hostname(self):
        return self.request.headers['Host']

    def set_error(self, debug_mode, code=httplib.INTERNAL_SERVER_ERROR, message=None):
        message = message or httplib.responses.get(code, 'Unknown Error')
        self.error(code)
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.clear()
        self.response.out.write(message)

    def handle_exception(self, exception, debug_mode):
        if isinstance(exception, HTTPStatusCode):
            self.set_error(debug_mode, code=exception.code, message=exception.message)
        else:
            self.set_error(debug_mode)

            logging.exception(exception)

            if debug_mode:
                self.response.out.write('\n\n')
                for line in traceback.format_exception(*sys.exc_info()):
                    self.response.out.write(line)
                    self.response.out.write('\n')
