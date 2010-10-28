import cgi
import re

from google.appengine.api import users

from pushmaster import config, logic, model, timezone, urls, util, query
from pushmaster.taglib import Literal, T, XHTML
import www

linkify_re = re.compile(r'\b(https?://[^\s]+)', re.MULTILINE | re.IGNORECASE)
http_re = re.compile(r'https?://', re.IGNORECASE)

def linkify_repl(m):
    return m.group(1) + link + m.group(3)

def linkify(text):
    if not text:
        return ''

    parts = []
    for part in linkify_re.split(text):
        m = http_re.match(part)
        if m:
            parts.append('<a href="%s">%s</a>' % (cgi.escape(part, quote=True), cgi.escape(part)))
        else:
            parts.append(cgi.escape(part))
    return Literal(''.join(parts).replace('\n', '<br/>'))

def display_datetime(dt):
    return T.span(class_='datetime')(util.format_datetime(dt))

def display_date(d):
    return T.span(class_='date')(util.format_date(d))

def navbar(current=None):
    nav = T.div(class_='nav')(
        T.a(href='/push/current')(T.span('Current Push')),
        T.span(class_='sep')('|'),
        T.a(href='/requests')('Requests'),
        T.span(class_='sep')('|'),
        T.a(href='/pushes')('Pushes'),
        T.span(class_='sep')('|'),
        T.a(href='/lastweek')('Last Week'),
        )
    return nav

def funcbar():
    bar = T.div(class_='func')(
        T.a(id='new-request', href='#')('Make Request'),
        T.span(class_='sep')('|'),
        T.a(id='new-push', href='#')('Start Push'),
        T.span(class_='sep')('|'),
        T.a(id='details', href='#')(T.span('Show Details', class_='show'), T.span('Hide Details', class_='hide')),
        )
    return bar

def session():
    user = users.get_current_user()

    div = T.div(class_='session')(
        user_home_link(user, logic.user_info(user)),
        T.span(class_='sep')('|'),
        T.a(href=users.create_logout_url('/'))('Logout')
    )
    return div

def push_email(push, children):
    mailto = 'mailto:push-%(key)s@%(host)s' % {'key': push.key(), 'host': config.mail_host}
    return T.a(children, href=mailto, class_='push-email')

def user_email(user):
    return T.a(href='mailto:' + user.email())(user.nickname())

def user_home_link(user, user_info):
    return T.span(class_='email')(T.a(href=urls.user_home(user))(user_info.full_name))

def display_user_email(user):
    return T.span(class_='email')(user_email(user)),

def push_plans_badge(_=None):
    return T.a(class_='push-plans badge', href=config.push_plans_url, title='This request has push plans.')('Push Plans')

def js_serials_badge(_=None):
    return T.span(class_='js-serials badge', title='This request requires the pushmaster to bump Javascript serials.')('JS')

def img_serials_badge(_=None):
    return T.span(class_='img-serials badge', title='This request requires the pushmaster to bump image serials.')('Image')

def tests_pass_badge(request):
    return T.span(class_='tests-pass badge', title='All Buildbot tests pass for this request.')(
        T.a(href=request.tests_pass_url or '#')('BB Tested')
        )

request_flags_badge_map = (
    ('push_plans', push_plans_badge),
    ('tests_pass', tests_pass_badge),
    ('js_serials', js_serials_badge),
    ('img_serials', img_serials_badge),
    )

def request_badges(request):
    return [badge(request) for flag, badge in request_flags_badge_map if getattr(request, flag)]

def request_item(request):
    li = T.li(class_='request clearfix')(
        display_date(request.target_date),
        T.span(class_='email')(T.a(href=urls.user_home(request.owner))(logic.user_info(request.owner).full_name), ':'),
        T.a(href=request.uri, class_='request-subject')(request.subject),
        )

    if request.target_date > util.tznow().date():
        li.attrs['class'] += ' future'

    if request.urgent:
        li.attrs['class'] += ' urgent'

    if request.state == 'rejected':
        li.attrs['class'] += ' rejected'

    if request.owner == users.get_current_user():
        li.attrs['class'] += ' own'

    li(request_badges(request), T.span(request.branch, class_='branch'), T.div(linkify(request.message), class_='message'))

    return li

def request_list(requests):
    return T.ol(class_='requests')(map(request_item, requests))

def take_ownership_form(object):
    form = T.form(class_='small', action=object.uri, method='post')(
        T.div(class_='fields')(
            T.button(type='submit', name='act', value='take_ownership')('Take Ownership'),
            ),
        )
    return form

def new_request_form(push=None, subject='', message='', branch=''):
    label = T.a(class_='toggle', href='#')('New Request') if push else 'New Request'
    class_ = 'push request' if push else 'request'
    content = T.div(class_='content')
    form = T.form(action='/requests', method='post', class_=class_)(
        T.fieldset(class_='container')(
            T.legend(label),
            content(
                T.div(
                    T.label(for_='new-request-subject')('Subject'),
                    T.input(name='subject', id='new-request-subject', value=subject),
                    ),
                T.div(
                    T.label(for_='new-request-branch')('Branch'),
                    T.input(name='branch', id='new-request-branch', value=branch),
                    ),
                T.div(
                    T.label(for_='new-request-message')('Message'),
                    T.textarea(name='message', id='new-request-message', rows='40', cols='120')(message),
                    ),
                T.div(
                    T.label(for_='new-request-target-date')('Push Date'),
                    T.input(name='target_date', id='new-request-target-date', class_='date', value=util.tznow().date().strftime('%Y-%m-%d')),
                    ),
                T.fieldset(class_='flags')(
                    T.legend('Flags'),
                    T.div(
                        T.input(id='new-request-urgent', type='checkbox', name='urgent', class_='checkbox'),
                        T.label(for_='new-request-urgent', class_='checkbox')('Urgent (e.g. P0)'),
                        ),
                    T.div(
                        T.input(id='new-request-tests-pass', type='checkbox', name='tests_pass', class_='checkbox'),
                        T.label(for_='new-request-tests-pass', class_='checkbox')('Passes Buildbot'),
                        T.input(id='new-request-tests-pass-url', name='tests_pass_url', class_='tests-pass-url'),
                        ),
                    T.div(
                        T.input(id='new-request-push-plans', type='checkbox', name='push_plans', class_='checkbox'),
                        T.label(class_='checkbox', for_='new-request-push-plans')('Push Plans'),
                        ),
                    T.div(
                        T.input(id='new-request-js-serials', type='checkbox', name='js_serials', class_='checkbox'),
                        T.label(class_='checkbox', for_='new-request-js-serials')('Bump Javascript Serials'),
                        ),
                    T.div(
                        T.input(id='new-request-img-serials', type='checkbox', name='img_serials', class_='checkbox'),
                        T.label(class_='checkbox', for_='new-request-img-serials')('Bump Image Serials'),
                        ),
                    ),
                T.button(type='submit')('Create')
                ),
            ),
        )
    if push:
        content(T.input(type='hidden', name='push', value=str(push.key())))
    return form

def new_push_form():
    return T.form(action='/pushes', method='post', class_='new-push')(
        T.div(class_='fields')(
            T.input(type='hidden', name='act', value='new_push'),
            T.div(T.label(for_='new-push-name')('Name:')),
            T.div(T.input(type='text', name='name', class_='push-name', id='new-push-name')),
            T.div(T.button(type='submit', class_='submit')('Start New Push')),
            ),
        )

def sendtostage_form():
    return T.form(action='#', method='post', class_='send-to-stage')(
        T.div(class_='fields')(
            T.input(type='hidden', name='act', value='sendtostage'),
            T.div(T.label(for_='dest-stage')('Destination:')),
            T.div(
                T.select(name='stage', class_='dest-stage', id='dest-stage')(
                    (T.option(value=stage)(stage)) for stage in model.Push.all_stages
                    ),
                ),
            ),
            T.div(T.button(type='submit', class_='submit')('Mark Deployed to Stage')),
        )

def reject_request_form():
    return T.form(action='#', method='post', class_='reject-request', id='reject-request-form')(
        T.div(class_='fields')(
            hidden(act='reject', push='true', return_url=''),
            T.h2(class_='subject'),
            T.label(for_='reject-request-reason')(
                T.span('Reason:'),
                T.div(T.textarea(name='reason', id='reject-request-reason')),
                ),
            T.div(T.button(type='submit', class_='submit')('Reject')),
            ),
        )

def bookmarklet(hostname):
    return T.span(
        T.span('Bookmark the following link to generate a request from within Review Board: '),
        T.a(href='javascript:$.getScript("%s://%s/bookmarklet");' % (config.protocol, hostname))('Pushmaster App: Create Request'),
        )

def hidden(**kw):
    return [T.input(type='hidden', name=name, value=value) for name, value in kw.items()]

def can_edit_request(request, push=None):
    current_user = users.get_current_user()
    push = push or request.push
    return (request.owner == current_user) or (push and (push.owner == current_user))

display_push_state_map = {
    'accepting': 'Accepting',
    'onstage': 'On Stage (%(stage)s)',
    'live': 'Live',
    'abandoned': 'Abandoned',
    }

def display_push_state(push):
    return display_push_state_map.get(push.state, 'Unknown') % {'stage': push.stage}

favicon = T.link(rel='shortcut icon', type='image/x-icon', href=config.favicon)
meta_content_type = T.meta(**{ 'http-equiv': 'Content-type', 'content': 'text/html;charset=UTF-8' })
feed_link = T.link(type='application/atom+xml', rel='alternate', title='Atom Feed', href=urls.atom_feed)

def stylesheet(href, external=False):
    return T('link', rel='stylesheet', href=href if external else urls.static_url(href))

def script(src, external=False):
    return T.script(type='text/javascript', src=src if external else urls.static_url(src))


reset_css = stylesheet(config.reset_css, external=True)
jquery_ui_css = stylesheet('/css/smoothness/jquery-ui-1.8.custom.css')
pushmaster_css = stylesheet('/css/pushmaster.css')

jquery_js = script(config.jquery, external=True)
jquery_ui_js = script(config.jquery_ui, external=True)
pushmaster_js = script('/js/pushmaster.js')

class Document(XHTML):
    def __init__(self, title='pushmaster'):
        super(Document, self).__init__()
        self.title = T.title(title) if title else T.title()
        self.head = T.head(
            meta_content_type,
            self.title,
            favicon,
            feed_link,
            reset_css,
            jquery_ui_css,
            pushmaster_css,
            )

        self.dialogs = T.div(id='dialogs')
        self.scripts = T.div(jquery_js, jquery_ui_js, pushmaster_js, id='scripts')

        request_form = new_request_form()
        request_form(id='new-request-form')
        self.dialogs(request_form)

        push_form = new_push_form()
        push_form(id='new-push-form')
        self.dialogs(push_form)

        stage_form = sendtostage_form()
        stage_form(id='sendtostage-form')
        self.dialogs(stage_form)

        reject_form = reject_request_form()
        self.dialogs(reject_form)

        self.funcbar = funcbar()
        self.body = T.body(session(), navbar(), self.funcbar)
        self.html(self.head, self.body)

    def serialize(self, f):
        self.body(self.dialogs, self.scripts)
        try:
            return super(Document, self).serialize(f)
        finally:
            self.body.children.remove(self.dialogs)
            self.body.children.remove(self.scripts)

def request_state_display(state):
    return {
        'requested': 'Requested',
        'accepted': 'Accepted',
        'checkedin': 'Checked In',
        'onstage': 'On Stage',
        'tested': 'Verified',
        'live': 'Live',
        'abandoned': 'Abandoned',
        'rejected': 'Rejected',
        }[state]
