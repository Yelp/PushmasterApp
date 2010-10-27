import datetime
import httplib
import logging

from django.utils import simplejson as json
from google.appengine.api import users
from google.appengine.api.datastore_errors import BadKeyError
from google.appengine.ext import db

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


class Search(RequestHandler):
    def get(self):
        self.response.headers['Cache-Control'] = 'no-cache'
        self.response.headers['Content-Type'] = 'application/json'
        results_dict = self.query()
        return json.dump(results_dict, self.response.out)


    #
    # generalized field parsers
    #


    def parse_owner(self, query):
        owner_field = self.request.get('owner')
        if owner_field:
            owner = users.User(owner_field)
            query.filter('owner =', owner)
        return query


    def parse_state(self, query):
        state_field = self.request.get('state')
        if state_field:
            query.filter('state =', state_field)
        return query


    #
    # query constructors
    #


    def query(self):
        # build query
        query = None
        model_field = self.request.get('model')
        if model_field == 'request':
            query = self.request_query()
        elif model_field == 'push':
            query = self.push_query()
        else:
            return {'results': [], 'cursor': None}

        # cursor
        cursor_field = self.request.get('cursor')
        if cursor_field:
            query.with_cursor(cursor_field)

        # order
        for order_field in self.request.get_all('order'):
            query.order(order_field)

        # how many results to fetch
        limit = 10
        limit_field = self.request.get('limit')
        if limit_field:
            try:
                limit = min(100, int(limit_field))
            except ValueError:
                pass

        # execute
        results = query.fetch(limit)
        cursor = query.cursor() if results else None

        return {'results': [result.json for result in results], 'cursor': cursor}


    def push_query(self):
        query = db.Query(model.Push)
        self.parse_owner(query)
        self.parse_state(query)

        return query


    def request_query(self):
        query = db.Query(model.Request)
        self.parse_owner(query)
        self.parse_state(query)

        # limited to a push
        push_field = self.request.get('push')
        if push_field:
            if push_field == 'current':
                push = query.current_push()
                if push:
                    query.filter('push =', push)
            else:
                push_key = db.Key(push_field)
                query.filter('push =', push_key)

        return query
