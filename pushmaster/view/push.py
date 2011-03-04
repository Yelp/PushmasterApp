import datetime
import httplib
import logging

from django.utils import simplejson as json
from google.appengine.api import users
from google.appengine.api.datastore_errors import BadKeyError
from google.appengine.ext import db
import yaml

from pushmaster.taglib import T, ScriptCData
from pushmaster import config, logic, model, query, urls, util
from pushmaster.view import common, HTTPStatusCode, RequestHandler

__author__ = 'Jeremy Latt <jlatt@yelp.com>'
__all__ = ('Pushes', 'EditPush')

log = logging.getLogger('pushmaster.view.push')

def push_item(push):
    requests = query.push_requests(push)
    return T.li(class_='push')(
        T.div(
            common.display_datetime(push.ptime),
            T.a(href=push.uri)(push.name or 'push'),
            common.user_home_link(push.owner, logic.user_info(push.owner)),
            T.span(class_='state')(common.display_push_state(push)),
            class_='headline',
            ),
        T.ol(map(common.request_item, requests)) if requests else T.div('No requests.'),
    )

class Pushes(RequestHandler):
    def get(self):
        doc = common.Document(title='pushmaster: recent pushes')

        pushes = query.open_pushes()

        doc.body(T.h1('Recent Pushes'), T.ol(map(push_item, pushes), class_='requests'))
        doc.serialize(self.response.out)

    def post(self):
        action = self.request.get('act')

        if action == 'new_push':
            name = self.request.get('name')
            push = logic.create_push(name=name)
            self.redirect(push.uri)
        else:
            raise HTTPStatusCode(httplib.BAD_REQUEST)

def accepted_list(accepted, request_item=common.request_item, state=''):
    return T.ol(class_=' '.join(['requests', state]))(map(request_item, accepted))

def push_pending_list(push, requests):
    is_push_owner = users.get_current_user() == push.owner
    def request_item(request):
        li = common.request_item(request)
        if is_push_owner:
            li.children.insert(0, T.div(class_='actions')(
                    T.form(class_='small', action=request.uri, method='post')(
                        T.div(class_='fields')(
                            T.button(type='submit')('Accept'),
                            common.hidden(push=str(push.key()), act='accept')),
                        ),
                    T.span('or', class_='sep'),
                    reject_request_link(request),
                    ),
               )
        return li
    ol = T.ol(class_='requests')
    if requests:
        ol(map(request_item, requests))
    return ol

def push_actions_form(push, requests):
    form = T.form(action=push.uri, method='post', class_='small')
    fields = T.div(class_='fields')
    form(fields)

    button_count = 0

    if push.state in ('accepting', 'onstage') and filter(lambda r: r.state == 'checkedin', requests):
        if button_count:
            fields(T.span(' or '))
        fields(T.button(type='button', name='sendtostage', id='send-to-stage', value=push.uri)('Mark Deployed to Stage'))
        button_count +=1

    if push.state == 'onstage' and requests and all(r.state == 'tested' for r in requests):
        if button_count:
            fields(T.span(' or '))
        fields(T.button(type='submit', name='act', value='sendtolive')('Mark Live'))
        button_count +=1

    if push.state in ('accepting', 'onstage'):
        if button_count:
            fields(T.span(' or '))
        fields(T.button(type='submit', name='act', value='abandon')('Abandon'))
        button_count +=1

    return form

def mark_checked_in_form(request):
    return T.form(class_='small', method='post', action=request.uri)(
        T.div(class_='fields')(
            T.button(type='submit')('Mark Checked In'),
            common.hidden(push='true', act='markcheckedin')))

def withdraw_form(request):
    return T.form(class_='small', method='post', action=request.uri)(
        T.div(class_='fields')(
            T.button(type='submit')('Withdraw'),
            common.hidden(push='true', act='withdraw')))

def mark_tested_form(request):
    return T.form(class_='small', method='post', action=request.uri)(
        T.div(class_='fields')(
            T.button(type='submit')('Mark Verified'),
            common.hidden(push='true', act='marktested')))

def reject_request_link(request):
    return T.a('Reject', class_='reject-request', href=request.uri, title=request.subject)

class EditPush(RequestHandler):
    def get_request_header_list(self, header, default=''):
        hval = self.request.headers.get(header, default)
        return [part.strip() for part in hval.split(',')]

    def get(self, push_id):
        push = None

        if push_id == 'current':
            push = query.current_push()
            self.redirect(push.uri if push else '/pushes')
            return

        try:
            push = model.Push.get(push_id)
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)

        current_user = users.get_current_user()
        pending_requests = query.pending_requests(not_after=util.tznow().date()) if current_user == push.owner else []

        if 'application/json' in self.get_request_header_list('Accept', default='*/*'):
            requests = query.push_requests(push)
            push_div = self.render_push_div(current_user, push, requests, pending_requests)
            response = {'push': dict(key=unicode(push.key()), state=push.state), 'html': unicode(push_div)}
            self.response.headers['Vary'] = 'Accept'
            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Cache-Control'] = 'no-store'
            self.response.out.write(json.dumps(response))

        else:
            doc = self.render_doc(current_user, push, pending_requests)
            self.response.out.write(unicode(doc))

    def render_doc(self, current_user, push, pending_requests):
        doc = common.Document(title='pushmaster: push: %s %s' % (util.format_datetime(push.ptime), push.name))
        doc.funcbar(T.span('|', class_='sep'), common.push_email(push, 'Send Mail to Requesters'))

        requests = query.push_requests(push)
        push_div = self.render_push_div(current_user, push, requests, pending_requests)
        doc.body(push_div)

        doc.scripts(common.script('/js/push.js'))
        push_json = ScriptCData('this.push = %s;' % json.dumps(dict(key=str(push.key()), state=push.state)))
        doc.head(T.script(type='text/javascript')(push_json))

        return doc

    def render_push_div(self, current_user, push, requests, pending_requests):
        push_div = T.div(class_='push')

        if current_user == push.owner:
            push_div(push_actions_form(push, requests)(class_='small push-action'))
        elif push.can_change_owner:
            push_div(common.take_ownership_form(push)(class_='small push-action'))

        header = T.h1(common.display_datetime(push.ptime), T.span(class_='name')(push.name or ''), common.user_home_link(push.owner, logic.user_info(push.owner)))

        if any(request.push_plans for request in requests):
            header(common.push_plans_badge())

        if any(request.js_serials for request in requests):
            header(common.js_serials_badge())

        if any(request.img_serials for request in requests):
            header(common.img_serials_badge())

        push_div(header)
        requests_div = T.div(class_='requests')
        push_div(requests_div)

        def requests_with_state(state):
            return filter(lambda r: r.state == state, requests)

        if push.state == 'live':
            requests_div(accepted_list(requests_with_state('live'), state='live'))
        else:
            def onstage_request_item(request):
                li = common.request_item(request)
                if current_user == push.owner:
                    li.children.insert(0, T.div(class_='actions')(mark_tested_form(request), T.span('or', class_='sep'), withdraw_form(request)))
                elif current_user == request.owner:
                    li.children.insert(0, T.div(class_='actions')(mark_tested_form(request)))
                return li

            def withdrawable_request_item(request):
                li = common.request_item(request)
                if current_user == push.owner:
                    li.children.insert(0, T.div(class_='actions')(withdraw_form(request)))
                return li

            def accepted_request_item(request):
                li = common.request_item(request)
                if current_user == push.owner:
                    li.children.insert(0, T.div(class_='actions')(
                            mark_checked_in_form(request),
                            T.span('or', class_='sep'),
                            withdraw_form(request),
                            T.span('or', class_='sep'),
                            reject_request_link(request),
                            ))
                return li

            request_states = [
                ('Verified on Stage', 'tested', withdrawable_request_item),
                ('On Stage (%s)' % push.stage, 'onstage', onstage_request_item),
                ('Checked In', 'checkedin', withdrawable_request_item),
                ('Accepted', 'accepted', accepted_request_item),
                ]
            for label, state, request_item in request_states:
                subrequests = requests_with_state(state)
                if subrequests:
                    if len(subrequests) > 5:
                        label = '%(label)s (%(count)d)' % {'label': label, 'count': len(subrequests)}
                    requestors = ', '.join(set(request.owner.nickname() for request in subrequests))
                    label = '%(label)s - %(requestors)s' % {'label': label, 'requestors': requestors}
                    requests_div(T.h3(label), accepted_list(subrequests, request_item=request_item, state=state))

        if current_user == push.owner:
            accepted_requests = requests_with_state('accepted')
            if accepted_requests:
                requests_div(T.div('cherry-pick-branches %s' % (' '.join(['"%s"' % request.branch for request in accepted_requests if request.branch]),), class_='code'))

        if push.editable:
            if pending_requests:
                pending_requests_title = ('Pending Requests (%d)' % len(pending_requests)) if len(pending_requests) > 5 else 'Pending Requests'
                push_div(T.h2(class_='pending')(pending_requests_title), push_pending_list(push, pending_requests))

        return push_div

    def post(self, push_id):
        try:
            push = model.Push.get(push_id)
        except BadKeyError:
            raise HTTPStatusCode(httplib.NOT_FOUND)

        action = self.request.get('act')

        if action == 'sendtostage':
            stage = self.request.get('stage')
            logic.send_to_stage(push, stage)
            self.redirect(push.uri)

        elif action == 'sendtolive':
            logic.send_to_live(push)
            self.redirect(push.uri)

        elif action == 'abandon':
            logic.abandon_push(push)
            self.redirect('/pushes')

        elif action == 'take_ownership':
            logic.take_ownership(push)
            self.redirect(push.uri)

        else:
            raise HTTPStatusCode(httplib.BAD_REQUEST)
