import httplib
import urllib

from google.appengine.api import memcache, users

from pushmaster import config
from pushmaster import model
from pushmaster import query
from pushmaster.taglib import T, XHTML
from pushmaster.view import common
from pushmaster.view import RequestHandler, HTTPStatusCode
import www

__author__ = 'Jeremy Latt <jlatt@yelp.com>'
__all__ = ('Root', 'UserHome', 'Favicon', 'RedirectHandler', 'Bookmarklet', 'NotFound')

class RedirectHandler(RequestHandler):
    def get(self):
        self.redirect(self.url)

def push_item(push):
    return T.li(class_='push')(
        T.a(href=push.uri)(common.display_datetime(push.ctime)),
        T.span(common.display_push_state(push)),
        )

def request_item(request):
    item = common.request_item(request)
    item(T.span(class_='state')(request.state))
    return item

class Root(RequestHandler):
    def get(self):
        push = query.current_push()
        if push:
            return self.redirect(push.uri)
        else:
            return self.redirect('/user/' + users.get_current_user().email())

class FlushMemcache(RequestHandler):
	def get(self):
		memcache.flush_all()

class UserHome(RequestHandler):
    def get(self, email):
        email = urllib.unquote_plus(email)
        
        doc = common.Document(title='pushmaster: recent activity: ' + email)

        doc.body(T.div(class_='bookmarklet')(common.bookmarklet(self.hostname)))

        user = users.User(email)

        requests = query.requests_for_user(user)
        pushes = query.pushes_for_user(user)

        if requests:
            doc.body(
                T.h3('Recent Requests'),
                T.ol(class_='my requests')(map(request_item, requests)),
                )

        if pushes:
            doc.body(
                T.h3('Recent Pushes'),
                T.ol(class_='pushes')(map(push_item, pushes)),
                )

        doc.serialize(self.response.out)

class Favicon(RedirectHandler):
    url = config.favicon

class Bookmarklet(RedirectHandler):
    url = www.assets['/js/bookmarklet.js']

class NotFound(RequestHandler):
    def get(self):
        raise HTTPStatusCode(httplib.NOT_FOUND)

    def post(self):
        raise HTTPStatusCode(httplib.NOT_FOUND)
