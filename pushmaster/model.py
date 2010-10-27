import datetime

from google.appengine.api import memcache
from google.appengine.ext import db

import query
import timezone
import urls


__author__ = 'Jeremy Latt <jlatt@yelp.com>'

class ConfigModel(db.Model):

    timestamp = db.DateTimeProperty(auto_now_add=True)

    mail_domain = db.StringProperty()
    mail_sender = db.StringProperty()
    mail_to = db.StringProperty()
    mail_request = db.StringProperty()
    push_plans_url = db.StringProperty()
    git_branch_url = db.StringProperty()


class TrackedModel(db.Model):

    cuser = db.UserProperty(auto_current_user_add=True)

    ctime = db.DateTimeProperty(auto_now_add=True)

    muser = db.UserProperty(auto_current_user=True)

    mtime = db.DateTimeProperty(auto_now=True)


class Push(TrackedModel):

    all_states = ('accepting', 'onstage', 'live', 'abandoned')

    default_state = all_states[0]

    all_stages = ('stagea', 'stagex')

    default_stage = all_stages[0]

    owner = db.UserProperty(auto_current_user_add=True)

    state = db.StringProperty(choices=all_states, default=default_state)

    ltime = db.DateTimeProperty()

    name = db.StringProperty()

    stage = db.StringProperty(choices=all_stages, default=default_stage)

    @property
    def requests_cache_key(self):
        return 'push-requests-%s' % self.key()

    def bust_requests_cache(self):
        memcache.delete(self.requests_cache_key)

    @property
    def ptime(self):
        return self.ltime or self.ctime

    @property
    def uri(self):
        return urls.push(self)

    @property
    def can_change_owner(self):
        return self.state in ('accepting', 'onstage')

    editable = can_change_owner

    @property
    def api_uri(self):
        return urls.api_push(self)

    def put(self):
        try:
            return super(Push, self).put()
        finally:
            query.bust_push_caches()

    @property
    def json(self):
        return {'key': unicode(self.key()),
                'state': self.state,
                'owner': self.owner.email(),
                'name': self.name,
                'stage': self.stage,
                'ctime': self.ctime.strftime('%s') if self.ctime else '',
                'mtime': self.mtime.strftime('%s') if self.mtime else '',
                'ltime': self.ltime.strftime('%s') if self.ltime else '',
                'ptime': self.ptime.strftime('%s') if self.ptime else ''
               }


class Request(TrackedModel):

    all_states = ('requested', 'accepted', 'checkedin', 'onstage', 'tested', 'live', 'abandoned', 'rejected')

    default_state = all_states[0]

    owner = db.UserProperty(auto_current_user_add=True)

    subject = db.StringProperty(default='')

    branch = db.StringProperty(default='')

    message = db.TextProperty(default='')

    state = db.StringProperty(choices=all_states, default=default_state)

    reject_reason = db.TextProperty(default='')

    target_date = db.DateProperty()

    push_plans = db.BooleanProperty(default=False)

    js_serials = db.BooleanProperty(default=False)

    img_serials = db.BooleanProperty(default=False)

    urgent = db.BooleanProperty(default=False)

    tests_pass = db.BooleanProperty(default=False)

    tests_pass_url = db.StringProperty(default='')

    push = db.ReferenceProperty(Push, collection_name='requests')

    @property
    def uri(self):
        return urls.request(self)

    @property
    def api_uri(self):
        return urls.api_request(self)

    @property
    def editable(self):
        return self.state in ('requested', 'rejected')

    @property
    def can_change_owner(self):
        return self.state in ('requested', 'accepted', 'checkedin', 'onstage', 'rejected')

    @property
    def json(self):
        return {'key': unicode(self.key()),
                'owner': self.owner.email(),
                'subject': self.subject,
                'branch': self.branch,
                'message': self.message,
                'state': self.state,
                'reject_reason': self.reject_reason,
                'target_date': self.target_date.strftime("%D"),
                'push_plans': self.push_plans,
                'js_serials': self.js_serials,
                'img_serials': self.img_serials,
                'urgent': self.urgent,
                'tests_pass': self.tests_pass
               }


class UserInfo(TrackedModel):

    full_name = db.StringProperty(default='')

    user = db.UserProperty()


class ReportUser(TrackedModel):

    teams = db.StringListProperty(default=[])
    role = db.StringProperty(default='dev')

    user = db.UserProperty()
