import logging

from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from pushmaster import config, urls, util
from pushmaster.view import RequestHandler

log = logging.getLogger('pushmaster.tasks')

class AsyncMailHandler(RequestHandler):
    def post(self):
        to = self.request.get_all('to')
        subject = self.request.get('subject')
        body = self.request.get('body')

        assert to
        assert subject
        assert body

        kw = dict(sender=config.mail_sender, to=to, subject=subject, body=body)
        for optional in ('reply_to', 'html'):
            value = self.request.get(optional)
            if value:
                kw[optional] = value

        log.debug('sending mail: %r', kw)
        mail.send_mail(**kw)

class AsyncXMPPHandler(RequestHandler):
    def post(self):
        to = self.request.get('to')
        message = self.request.get('message')

        assert to
        assert message

        log.debug('sending im: to=%s, message=%s', to, message)
        util.maybe_send_im(to, message)

#
# the app
#

wsgi_app = [
    (urls.mail_task, AsyncMailHandler),
    (urls.xmpp_task, AsyncXMPPHandler),
    ]

def main():
    run_wsgi_app(webapp.WSGIApplication(wsgi_app))

if __name__ == '__main__':
    main()
