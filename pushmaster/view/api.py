import datetime
import httplib
import logging

from django.utils import simplejson as json
from google.appengine.api import users
from google.appengine.api.datastore_errors import BadKeyError

from pushmaster import model
from pushmaster import query
from pushmaster import util
from pushmaster.view import common
from pushmaster.view import HTTPStatusCode
from pushmaster.view import RequestHandler

__author__ = 'Matt Jones <mattj@yelp.com>'
__all__ = ('Pushes', 'EditPush')

log = logging.getLogger('pushmaster.view.api')

class Pushes(RequestHandler):
    def get(self):
        """List pushes"""
        pushes = query.open_pushes()
        response = {'pushes': [push.json for push in pushes]}
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(response))


class Request(RequestHandler):

    def get(self, request_key):
        """Show a request."""
        try:
            request = model.Request.get(request_key)
            self.response.headers['Content-Type'] = 'application/json'
            data = request.json
            data['message_html'] = unicode(common.linkify(request.message or ''))
            self.response.out.write(json.dumps(data))
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)


class Requests(RequestHandler):
    def get(self):
        """List requests"""
        requests = query.current_requests()
        response = {'requests': [request.json for request in requests]}

        self.response.out.write(json.dumps(response))


class EditPush(RequestHandler):
    def get(self, push_id):
        push = None

        if push_id == 'current':
            push = query.current_push()
            self.redirect(push.api_uri if push else '/pushes')
            return

        try:
            push = model.Push.get(push_id)
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)

        current_user = users.get_current_user()
        pending_requests = query.pending_requests(not_after=util.tznow().date()) if current_user == push.owner else []

        requests = query.push_requests(push)

        push_info = self.render_push_info(push, requests)
        request_info = self.render_request_info(pending_requests)

        response = {'push': push_info, 'pending_requests': request_info}

        self.response.headers['Vary'] = 'Accept'
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Cache-Control'] = 'no-store'

        self.response.out.write(json.dumps(response))

    def render_push_info(self, push, requests):
        push = push.json
        push['requests'] = [r.json for r in requests]

        return push

    def render_request_info(self, pending_requests):
        return [r.json for r in pending_requests]

