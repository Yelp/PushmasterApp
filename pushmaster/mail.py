import logging
import re

from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.api.datastore_errors import BadKeyError
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 

from pushmaster import config, logic, model, query, util

class PushMailHandler(InboundMailHandler):
    push_key_address_re = re.compile(r'push-(.+)')

    def receive(self, mail_message):
        sender = mail_message.sender
        logging.debug('got mail from %s', sender)

        text_bodies = [body for content_type, body in mail_message.bodies('text/plain')]
        if not text_bodies:
            return
        text_body = text_bodies[0] # TODO: support multiple bodies

        to = mail_message.to
        match = self.push_key_address_re.match(to)
        if match is None:
            logging.warning('failed to match push address: %s', to)
            return

        try:
            push_key = match.group(1)
            push = model.Push.get(push_key)
            requester_emails = [request.owner.email() for request in query.push_requests(push)]
            kw = dict(sender=sender, to=requester_emails, subject=mail_message.subject, body=text_body, reply_to=sender)
            logging.info('sending push mail: %r', kw)
            util.send_mail(**kw)
            
        except BadKeyError:
            logging.warning('failed to find push %s', push_key)

#
# the app
#

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

wsgi_app = [
    PushMailHandler.mapping(),
    ]

def main():
    run_wsgi_app(webapp.WSGIApplication(wsgi_app))

if __name__ == '__main__':
    main()
