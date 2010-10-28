from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from pushmaster import config
from pushmaster import urls
from pushmaster import util


def push_to_entry(push):
    pass


def request_to_entry(request):
    pass


class Atom(webapp.RequestHandler):
    template_path = 'pushmaster/view/atom.dtl'


    def get(self):
        entries = []
        context = dict(
            config=config,
            urls=urls,
            updated=util.tznow(),
            entries=entries,
            )
        rendered = template.render(self.template_path, context)
        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.response.out.write(rendered)
