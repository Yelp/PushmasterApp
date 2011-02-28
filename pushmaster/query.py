import datetime

from google.appengine.api import memcache
from google.appengine.ext import db

import model
import timezone

CACHE_SECONDS = 60 * 60 * 24

def push_requests(push, state=None):
    requests = memcache.get(push.requests_cache_key)
    if requests is None:
        requests = list(model.Request.all().filter('push =', push))
        requests = sorted(requests, key=lambda r: (not r.urgent, r.mtime))
        memcache.add(push.requests_cache_key, requests, CACHE_SECONDS)

    if state is not None:
        requests = filter(lambda r: r.state == state, requests)

    return requests

CURRENT_PUSH_CACHE_KEY = 'push-current'
OPEN_PUSHES_CACHE_KEY = 'push-open'
NO_CURRENT_PUSH = 'no-current-push'

def current_push():
    current_push = memcache.get(CURRENT_PUSH_CACHE_KEY)
    if current_push is None:
        states = ('accepting', 'onstage')
        current_pushes = list(model.Push.all().filter('state in', states).order('-ctime'))
        current_push = current_pushes[-1] if current_pushes else None
        memcache.add(CURRENT_PUSH_CACHE_KEY, current_push or NO_CURRENT_PUSH, CACHE_SECONDS)
    elif current_push == NO_CURRENT_PUSH:
        return None

    return current_push

def open_pushes():
    open_pushes = memcache.get(OPEN_PUSHES_CACHE_KEY)
    if open_pushes is None:
        states = ('accepting', 'onstage', 'live')
        open_pushes = model.Push.all().filter('state in', states).order('-ctime').fetch(25)
        open_pushes = sorted(open_pushes, key=lambda p: p.ptime, reverse=True)
        memcache.add(OPEN_PUSHES_CACHE_KEY, open_pushes, 60 * 60)
    return open_pushes

def pushes_for_user(user, limit=25):
    states = ('accepting', 'onstage', 'live')
    pushes = model.Push.all().filter('owner =', user).filter('state in', states).order('-mtime').fetch(limit)
    pushes = sorted(pushes, key=lambda p: p.ptime, reverse=True)
    return pushes

def pushes_for_the_week_of(from_date):
        from_date = from_date.astimezone(timezone.UTC())
        pushes = list(model.Push.all().filter('state =', 'live').filter('ltime >=', from_date).filter('ltime <', from_date + datetime.timedelta(days=7)).order('ltime'))
        return pushes

def bust_push_caches():
    memcache.delete_multi([CURRENT_PUSH_CACHE_KEY, OPEN_PUSHES_CACHE_KEY])

CURRENT_REQUESTS_CACHE_KEY = 'request-current'

def current_requests():
    requests = memcache.get(CURRENT_REQUESTS_CACHE_KEY)
    if requests is None:
        requests = model.Request.all().filter('state =', 'requested')
        requests = sorted(requests, key=lambda r: (not r.urgent, r.target_date, not r.tests_pass, r.mtime))
        memcache.add('request-current', requests, CACHE_SECONDS)

    return requests

def pending_requests(not_after=None):
    requests = current_requests()
    requests = filter(lambda r: r.state == model.Request.default_state, requests)
    if not_after is not None:
        requests = filter(lambda r: r.target_date <= not_after, requests)
    return requests

def requests_for_user(user, limit=25):
    states = ('requested', 'accepted', 'checkedin', 'onstage', 'tested', 'live', 'rejected')
    requests = model.Request.all().filter('state in', states).filter('owner =', user).order('-mtime').fetch(limit)
    requests = sorted(requests, key=lambda r: (r.target_date, r.ctime), reverse=True)
    return requests

def info_for_user(user):
    if user is None:
        return None

    user_info = memcache.get('user-info-%s' % user.nickname())
    if user_info is None:
        user_info = model.UserInfo.all().filter('user =', user).get()
        if user_info is not None:
            memcache.add('user-info-%s' % user.nickname(), user_info, CACHE_SECONDS)
    return user_info

def bust_request_caches():
    memcache.delete(CURRENT_REQUESTS_CACHE_KEY)

def report_users_by_team():
    users = model.ReportUser.all()

    teams = {}
    for u in users:
        for t in u.teams:
            teams.setdefault(t, {}).setdefault(u.role, []).append(u.user.nickname())

    return teams
