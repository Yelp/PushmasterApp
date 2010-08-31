__author__ = 'Jeremy Latt <jlatt@yelp.com>'

# fix up the environment before anything else
from pushmaster import tweaks

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from pushmaster import config
from pushmaster.view import api
from pushmaster.view import home
from pushmaster.view import request
from pushmaster.view import push
from pushmaster.view import report
from pushmaster.log import ClassLogger

class LoggingWSGIApplication(webapp.WSGIApplication):

    log = ClassLogger()

    def __call__(self, environ, start_response):
        request = self.REQUEST_CLASS(environ)
        self.log.debug('incoming %s for %s' % (environ['REQUEST_METHOD'], request.uri))
        return super(LoggingWSGIApplication, self).__call__(environ, start_response)

application = LoggingWSGIApplication([
        ('/requests', request.Requests),
        ('/pushes', push.Pushes),
        ('/api/pushes', api.Pushes),
        ('/request/([^/]+)', request.EditRequest),
        ('/push/(.+)', push.EditPush),
        ('/api/push/(.+)', api.EditPush),
        ('/api/request/(.+)', api.Request),
        ('/api/requests', api.Requests),
        ('/lastweek/(\d+)', report.LastWeek),
        ('/lastweek/?', report.LastWeek),
        ('/flush', home.FlushMemcache),
        ('/user/(.+)', home.UserHome),
        ('/favicon.ico', home.Favicon),
        ('/bookmarklet', home.Bookmarklet),
        ('/', home.Root),
        ('.*', home.NotFound),
        ], debug=config.debug)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
