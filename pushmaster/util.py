import cgi
import datetime
import logging
import os

from google.appengine.api import xmpp
from google.appengine.api.labs import taskqueue

from pushmaster import config, timezone, urls


log = logging.getLogger('pushmaster.util')

def send_mail(**kw):
    required = ('to', 'subject', 'body')
    for key in required:
        assert kw.get(key)
    allowed = required + ('html', 'reply_to', 'cc')
    params = dict((key, value) for key, value in kw.iteritems() if (key in allowed and value))

    taskqueue.Queue(name='mail').add(taskqueue.Task(url=urls.mail_task, params=params))

def send_im(to=None, message=None, **kw):
    assert to
    assert message
    if kw:
        kw = dict((key, cgi.escape(value)) for key, value in kw.iteritems())
        message = message % kw
    taskqueue.Queue(name='xmpp').add(taskqueue.Task(url=urls.xmpp_task, params=dict(to=to, message=message)))

def tznow(tz=config.tzinfo):
    return datetime.datetime.now(tz)

def choose_strftime_format(dt):
    now = tznow()
    
    strftime_format = '%e %b %Y' # 15 Sep 2009
    if dt.date().year == now.date().year:
        if dt.date().month == now.date().month:
            if dt.date().day == now.date().day:
                strftime_format = '%l:%M %p' # 3:07 PM
            elif (now.date() - dt.date()) < datetime.timedelta(days=7):
                strftime_format = '%a %l:%M %p' # Wed 3:07 PM
            else:
                strftime_format = '%a, %e %b' # Wed, 20 Jan
    return strftime_format

def format_datetime(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.UTC())
    dt = dt.astimezone(config.tzinfo) 
    return dt.strftime(choose_strftime_format(dt))

def choose_date_strftime_format(d):
    today = tznow().date()
    strftime_format = '%e %b %Y' # 15 Sep 2009
    if d.year == today.year:
        if d.month == today.month:
            if d.day == today.day:
                strftime_format = 'today'
            elif d.day == (today.day + 1):
                strftime_format = 'tomorrow'
            elif d.day == (today.day - 1):
                strftime_format = 'yesterday'
            else:
                strftime_format = '%a, %e %b' # Wed, 20 Jan
        else:
            strftime_format = '%e %b' # 15 Sep
    return strftime_format
            
def format_date(d):
    return d.strftime(choose_date_strftime_format(d))

def maybe_send_im(to, msg):
    if xmpp.get_presence(to):
        xmpp.send_message(to, '<html xmlns="http://jabber.org/protocol/xhtml-im"><body xmlns="http://www.w3.org/1999/xhtml">%s</body></html>' % msg, raw_xml=True)
