import datetime
import httplib
import logging

from google.appengine.api import users
from google.appengine.api.datastore_errors import BadKeyError

from pushmaster import config
from pushmaster import logic
from pushmaster import query
from pushmaster import util
from pushmaster.model import *
from pushmaster.taglib import T
from pushmaster.view import common
from pushmaster.view import HTTPStatusCode
from pushmaster.view import RequestHandler

__author__ = 'Jeremy Latt <jlatt@yelp.com>'
__all__ = ('Requests', 'EditRequest')

def edit_request_form(request):
    request_id = str(request.key())
    return T.form(action=request.uri, method='post', class_='edit request')(
        T.fieldset(class_='container')(
            T.legend(T.a(class_='toggle', href='#')('Edit Request')),
            T.div(class_='content')(
                T.div(
                    T.label(for_='edit-request-subject-'+request_id)('Subject'),
                    T.input(name='subject', id='edit-request-subject-'+request_id, value=request.subject),
                    ),
                T.div(
                    T.label(for_='edit-request-branch-'+request_id)('Branch'),
                    T.input(name='branch', id='edit-request-branch-'+request_id, value=request.branch or ''),
                    ),
                T.div(
                    T.label(for_='edit-request-message-'+request_id)('Message'),
                    T.textarea(name='message', id='edit-request-message-'+request_id)(request.message or ''),
                    ),
                T.div(
                    T.label(for_='edit-request-target-date-'+request_id)('Push Date'),
                    T.input(name='target_date', id='edit-request-target-date-'+request_id, class_='date', value=request.target_date.strftime('%Y-%m-%d') if request.target_date else ''),
                    ),
                T.fieldset(class_='flags')(
                    T.legend('Flags'),
                    T.div(
                        T.input(id='edit-request-urgent-'+request_id, type='checkbox', name='urgent', class_='checkbox', checked=request.urgent),
                        T.label(for_='edit-request-urgent-'+request_id, class_='checkbox')('Urgent (e.g. P0)'),
                        ),
                    T.div(
                        T.input(id='edit-request-tests-pass-'+request_id, type='checkbox', name='tests_pass', checked=request.tests_pass, class_='checkbox'),
                        T.label(for_='edit-request-tests-pass-'+request_id, class_='checkbox')('Passes Buildbot'),
                        T.input(id='edit-request-tests-pass-url-'+request_id, name='tests_pass_url', class_='tests-pass-url', value=request.tests_pass_url),
                        ),
                    T.div(
                        T.input(id='edit-request-push-plans-'+request_id, type='checkbox', name='push_plans', checked=request.push_plans, class_='checkbox'),
                        T.label(for_='edit-request-push-plans-'+request_id, class_='checkbox')('Push Plans'),
                        ),
                    T.div(
                        T.input(id='edit-request-js-serials-'+request_id, type='checkbox', name='js_serials', checked=request.js_serials, class_='checkbox'),
                        T.label(for_='edit-request-js-serials-'+request_id, class_='checkbox')('Bump Javascript Serials'),
                        ),
                    T.div(
                        T.input(id='edit-request-img-serials-'+request_id, type='checkbox', name='img_serials', checked=request.img_serials, class_='checkbox'),
                        T.label(for_='edit-request-img-serials-'+request_id, class_='checkbox')('Bump Image Serials'),
                        ),
                    ),
                T.div(
                    T.button(type='submit', name='act', value='edit')('Save'),
                    ),
                ),
            ),
        )

def request_actions_form(request):
    form = T.form(action=request.uri, method='post', class_='request-actions')

    if request.state in ('requested', 'rejected'):
        form(T.button(type='submit', name='act', value='abandon')('Abandon'))

    return form

def request_display(request, push):
    title = T.h2(class_='request-title')(
        T.span(class_='subject')(request.subject),
        common.user_home_link(request.owner, logic.user_info(request.owner)),
        common.display_date(request.target_date),
        )
    div = T.div(class_='request')(title)
    if request.branch:
        if '/' in request.branch:
            repo, _, branch = request.branch.partition('/')
            repo = 'devs/%s.git' % repo
        else:
            repo, branch = 'yelp-main.git', request.branch
        div(T.h3(T.span('Branch: '), T.a(request.branch, href=config.git_branch_url % dict(repo=repo,branch=branch))))

    if push:
        div(T.h3(T.span('Push: '), T.a('%s %s' % (util.format_datetime(push.ptime), push.name), href=push.uri)))

    if request.reject_reason:
        div(
            T.h3('Reject Reason:'),
            T.p(common.linkify(request.reject_reason), class_='reject-reason'),
            )

    div(T.div(class_='message')(common.linkify(request.message or '')))

    if request.urgent:
        title.attrs['class'] += ' urgent'

    title(common.request_badges(request))

    title(T.span(request.state, class_='state'))

    if not push or users.get_current_user() == push.owner:
        div(request_actions_form(request))

    return div

class Requests(RequestHandler):
    def get(self):
        requests = query.current_requests()

        doc = common.Document(title='pushmaster: requests')
        doc.body(
            T.h2(('Current Requests (%d)' % len(requests)) if len(requests) > 5 else 'Current Requests'),
            common.request_list(requests) if requests else T.span('There are no requests at present.'),
            T.div(common.bookmarklet(self.hostname)),
            )
        doc.serialize(self.response.out)
        
    def post(self):
        subject = self.request.get('subject')
        message = self.request.get('message')
        branch = self.request.get('branch') or None
        push_plans = self.request.get('push_plans', 'off')
        urgent = self.request.get('urgent', 'off')
        js_serials = self.request.get('js_serials', 'off')
        img_serials = self.request.get('img_serials', 'off')
        tests_pass = self.request.get('tests_pass', 'off')
        tests_pass_url = self.request.get('tests_pass_url', '')
        target_date = self.request.get('target_date')
        target_date = datetime.datetime.strptime(target_date, '%Y-%m-%d').date() if target_date else None

        try:
            assert push_plans in ('on', 'off'), 'push_plans must be either on or off'
            assert urgent in ('on', 'off'), 'urgent must be either on or off'
            assert js_serials in ('on', 'off'), 'js_serials must be on or off'
            assert img_serials in ('on', 'off'), 'img_serials must be on or off'
            assert tests_pass in ('on', 'off'), 'tests_pass must be on or off'
            assert len(subject) > 0, 'subject is required'
        except AssertionError, e:
            self.log.info('bad request: %s', e.message)
            raise HTTPStatusCode(httplib.BAD_REQUEST)

        request = logic.create_request(
            subject=subject, 
            message=message,
            push_plans=(push_plans == 'on'),
            urgent=(urgent == 'on'),
            js_serials=(js_serials == 'on'),
            img_serials=(img_serials == 'on'),
            tests_pass=(tests_pass == 'on'),
            tests_pass_url=tests_pass_url,
            target_date=target_date,
            branch=branch,
            )

        push = None
        push_key = self.request.get('push')
        if push_key:
            try:
                push = Push.get(push_key)
            except BadKeyError:
                pass
        self.redirect(push.uri if push else request.uri)

class EditRequest(RequestHandler):
    def get(self, request_id):
        try:
            request = Request.get(request_id)
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)

        doc = common.Document(title='pushmaster: request: ' + request.subject)

        push = request.push
        rdisplay = request_display(request, push)
        doc.body(rdisplay)

        if request.owner == users.get_current_user():
            if request.editable:
                doc.body(edit_request_form(request))
        elif request.can_change_owner:
            rdisplay(common.take_ownership_form(request))

        doc.serialize(self.response.out)

    def post(self, request_id):
        try:
            request = Request.get(request_id)
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)

        action = self.request.get('act')
        redirect_to_push = self.request.get('push') == 'true'

        if action == 'edit':
            subject = self.request.get('subject')
            assert len(subject) > 0, 'subject must have a value'
            message = self.request.get('message')
            branch = self.request.get('branch') or None
            target_date = self.request.get('target_date')
            target_date = datetime.datetime.strptime(target_date, '%Y-%m-%d').date() if target_date else None
            push_plans = self.request.get('push_plans', 'off')
            assert push_plans in ('on', 'off'), 'push plans must be on or off'
            urgent = self.request.get('urgent', 'off')
            assert urgent in ('on', 'off'), 'urgent must be on or off'
            js_serials = self.request.get('js_serials', 'off')
            assert js_serials in ('on', 'off'), 'js_serials must be on or off'
            img_serials = self.request.get('img_serials', 'off')
            assert img_serials in ('on', 'off'), 'img_serials must be on or off'
            tests_pass = self.request.get('tests_pass', 'off')
            assert tests_pass in ('on', 'off'), 'tests_pass must be on or off'
            tests_pass_url = self.request.get('tests_pass_url', '')
            logic.edit_request(
                request, 
                subject=subject, 
                message=message, 
                push_plans=push_plans == 'on', 
                urgent=urgent == 'on', 
                js_serials=js_serials == 'on', 
                img_serials=img_serials == 'on',
                tests_pass=(tests_pass == 'on'),
                tests_pass_url=tests_pass_url,
                target_date=target_date, 
                branch=branch,
                )
            self.redirect(request.uri)

        elif action == 'accept':
            push_id = self.request.get('push')
            push = Push.get(push_id)
            logic.accept_request(push, request)
            self.redirect(push.uri)

        elif action == 'abandon':
            logic.abandon_request(request)
            self.redirect('/requests')

        elif action == 'withdraw':
            push_uri = request.push.uri if request.push else None
            logic.withdraw_request(request)
            self.redirect(push_uri if (redirect_to_push and push_uri) else request.uri)

        elif action == 'markcheckedin':
            push_uri = request.push.uri if request.push else None
            logic.set_request_checkedin(request)
            self.redirect(push_uri if (redirect_to_push and push_uri) else request.uri)

        elif action == 'marktested':
            push_uri = request.push.uri if request.push else None
            logic.set_request_tested(request)
            self.redirect(push_uri if (redirect_to_push and push_uri) else request.uri)

        elif action == 'take_ownership':
            push_uri = request.push.uri if request.push else None
            logic.take_ownership(request)
            self.redirect(push_uri if (redirect_to_push and push_uri) else request.uri)

        elif action == 'reject':
            reason = self.request.get('reason')
            push_uri = request.push.uri if request.push else None
            if not push_uri:
                push_uri = self.request.get('return_url')
            logic.reject_request(request, users.get_current_user(), reason)
            self.redirect(push_uri if (redirect_to_push and push_uri) else request.uri)
        
        else:
            raise HTTPStatusCode(httplib.BAD_REQUEST)
