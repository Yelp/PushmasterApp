import logging
import datetime

from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import OverQuotaError

import config
import model
import query
import util

__author__ = 'Jeremy Latt <jlatt@yelp.com>'

log = logging.getLogger('pushmaster.logic')

def create_request(subject, **kw):
    return set_request_properties(model.Request(), subject, **kw)

def edit_request(request, subject, **kw):
    assert request.state in ('requested', 'rejected')
    return set_request_properties(request, subject, **kw)

def set_request_properties(request, subject, message=None, push_plans=False, urgent=False, js_serials=False, target_date=None, branch=None, img_serials=False, tests_pass=False, tests_pass_url=''):
    assert len(subject) > 0
    target_date = target_date or datetime.date.today()

    request.state = request.default_state
    request.reject_reason = None
    request.push = None
    request.subject = subject
    request.branch = branch and branch.strip()
    request.push_plans = push_plans
    request.js_serials = js_serials
    request.img_serials = img_serials
    request.tests_pass = tests_pass
    request.tests_pass_url = tests_pass_url
    request.urgent = urgent
    request.target_date = target_date
    if message:
        assert len(message) > 0
        request.message = message

    request.put()
    query.bust_request_caches()

    send_request_mail(request)

    return request

def send_request_mail(request):
    body = [request.message or request.subject]
    body.append(config.url(request.uri))

    util.send_mail(
        to=[request.owner.email(), config.mail_to, config.mail_request],
        subject='%s: %s' % (request.owner.nickname(), request.subject),
        body='\n'.join(body))

def abandon_request(request):
    assert request.state in ('requested', 'accepted', 'rejected')
    request.state = 'abandoned'
    push = request.push
    request.push = None

    request.put()
    query.bust_request_caches()
    if push is not None:
        push.bust_requests_cache()

    return request

def create_push(name=None):
    push = model.Push(name=name)

    push.put()
    query.bust_push_caches()

    return push

def abandon_push(push):
    assert push.state in ('accepting', 'onstage')

    push.state = 'abandoned'
    for request in query.push_requests(push):
        request.state = 'requested'
        request.push = None
        request.put()

    push.put()
    query.bust_push_caches()
    query.bust_push_caches()
    query.bust_request_caches()
    push.bust_requests_cache()

    return push

def accept_request(push, request):
    assert push.state in ('accepting', 'onstage')
    assert request.state == 'requested'
    assert not request.push

    request.push = push
    request.state = 'accepted'

    request.put()
    query.bust_request_caches()
    push.bust_requests_cache()

    util.send_im(
        to=request.owner.email(),
        message='<a href="mailto:%(pushmaster_email)s">%(pushmaster_name)s</a> accepted <a href="%(request_uri)s">%(request_subject)s</a> into <a href="%(push_uri)s">%(push_name)s</a>.',
        pushmaster_email=push.owner.email(),
        pushmaster_name=user_info(push.owner).full_name,
        request_uri=config.url(request.uri),
        request_subject=request.subject,
        push_uri=config.url(push.uri),
        push_name=push.name or 'the push',
        )

    return request

def withdraw_request(request):
    assert request.state in ('accepted', 'checkedin', 'onstage', 'tested')
    push = request.push
    assert push
    assert request.push.state in ('accepting', 'onstage')

    push_owner_email = request.push.owner.email()
    request.push = None
    request.state = 'requested'

    request.put()
    query.bust_request_caches()
    push.bust_requests_cache()

    util.send_mail(
        to=[push_owner_email, config.mail_to, config.mail_request],
        subject='Re: %s: %s' % (request.owner.nickname(), request.subject),
        body='I withdrew my request.\n' + config.url(request.uri))

    return request

def send_to_stage(push, stage):
    assert push.state in ('accepting', 'onstage')
    assert stage in model.Push.all_stages

    checkedin_requests = query.push_requests(push, state='checkedin')
    if checkedin_requests:
        if push.state != 'onstage' or push.stage != stage:
            push.state = 'onstage'
            push.stage = stage

            push.put()
            query.bust_push_caches()

        for request in checkedin_requests:
            request.state = 'onstage'
            owner_email = request.owner.email()

            util.send_mail(
                to=[owner_email, config.mail_to],
                subject='Re: %s: %s' % (request.owner.nickname(), request.subject),
                body=('Please verify your changes on %s.\n%s' % (push.stage, config.url(push.uri)))
                )

            util.send_im(
                to=owner_email,
                message='<a href="mailto:%(pushmaster_email)s">%(pushmaster_name)s</a> requests that you verify your changes on %(stage)s for <a href="%(push_uri)s">%(request_subject)s</a>.',
                pushmaster_email=push.owner.email(),
                pushmaster_name=user_info(push.owner).full_name,
                request_subject=request.subject,
                push_uri=config.url(push.uri),
                stage=push.stage,
                )
            request.put()

        push.bust_requests_cache()

    return push

def set_request_tested(request, bust_caches=True):
    assert request.state == 'onstage'
    push = request.push
    assert push

    request.state = 'tested'
    request.put()

    if bust_caches:
        push.bust_requests_cache()

    push_owner_email = push.owner.email()

    util.send_mail(
        to=[push_owner_email, config.mail_to],
        subject='Re: %s: %s' % (request.owner.nickname(), request.subject),
        body='Looks good to me.\n' + config.url(push.uri))

    if all(request.state == 'tested' for request in query.push_requests(push)):
        util.send_im(push_owner_email, 'All changes for <a href="%s">the push</a> are verified on stage.' % config.url(push.uri))

    return request

def send_to_live(push):
    assert push.state == 'onstage'
    requests = query.push_requests(push)
    for request in requests:
        assert request.state in ('tested', 'live')

    for request in requests:
        request.state = 'live'
        request.put()

    push.state = 'live'
    push.ltime = datetime.datetime.utcnow()

    push.put()
    query.bust_push_caches()
    push.bust_requests_cache()

    return push

def set_request_checkedin(request):
    assert request.state == 'accepted'
    push = request.push
    assert push

    request.state = 'checkedin'

    request.put()
    push.bust_requests_cache()

    util.send_mail(
        to=[push.owner.email(), config.mail_to],
        subject='Re: %s: %s' % (request.owner.nickname(), request.subject),
        body='Changes are checked in.\n' + config.url(push.uri))

    im_fields = dict(

        )
    util.send_im(
        to=request.owner.email(),
        message='Changes for <a href="%(request_uri)s">%(request_subject)s</a> are checked into <a href="%(push_uri)s">%(push_name)s</a>.',
        request_uri=config.url(request.uri),
        request_subject=request.subject,
        push_name=push.name or 'the push',
        push_uri=config.url(push.uri),
        )

    return request

def take_ownership(object):
    object.owner = users.get_current_user()

    object.put()

    if isinstance(object, model.Request):
        query.bust_request_caches()
        push = object.push
        if push is not None:
            object.push.bust_requests_cache()
    elif isinstance(object, model.Push):
        query.bust_push_caches()

    return object

def force_live(push):
    for request in query.push_requests(push):
        request.state = 'live'

        request.put()
    push.bust_requests_cache()

    push.state = 'live'
    push.ltime = push.mtime

    push.put()
    query.bust_push_caches()

    return push

def reject_request(request, rejector, reason=None):
    push = request.push

    request.push = None
    request.state = 'rejected'
    if reason:
        request.reject_reason = reason

    request.put()
    query.bust_request_caches()
    if push is not None:
        push.bust_requests_cache()

    util.send_im(
        to=request.owner.email(),
        message='<a href="mailto:%(rejector_email)s">%(rejector_name)s</a> rejected your request <a href="%(request_uri)s">%(request_subject)s</a>: %(reason)s',
        rejector_email=rejector.email(),
        rejector_name=user_info(rejector).full_name,
        request_subject=request.subject,
        request_uri=config.url(request.uri),
        reason=reason,
        )

    util.send_mail(
        to=[request.owner.email(), config.mail_to, config.mail_request],
        subject='Re: %s: %s' % (request.owner.nickname(), request.subject),
        body="""This request was rejected.\n\n%s\n\n%s""" % (reason, config.url(request.uri)),
        )

    return request


def create_user_info(user):
    user_info = model.UserInfo(user=user, full_name=user.nickname())

    user_info.put()

    return user_info

def user_info(user):
    return query.info_for_user(user) or create_user_info(user)


def unlive(push):
    push.state = 'onstage'
    push.put()
    for request in push.requests:
        request.state = 'tested'
        request.put()
    push.bust_requests_cache()
    query.bust_push_caches()
