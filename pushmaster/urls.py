import www

__author__ = 'jlatt@yelp.com'

def report(d):
    return '/report/%d%02d%02d' % (d.year, d.month, d.day)

def push(p):
    return '/push/' + str(p.key())

def request(r):
    return '/request/' + str(r.key())

def api_push(p):
    return '/api/push/' + str(p.key())

def api_request(r):
    return '/api/request/' + str(r.key())

def user_home(u):
    return '/user/' + u.email()

pushes = '/pushes'

requests = '/requests'

reports = '/reports'

def static_url(path):
    return www.assets[path]

mail_task = '/tasks/mail'

xmpp_task = '/tasks/xmpp'
