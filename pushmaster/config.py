import os
import timezone
from model import ConfigModel

try:
    is_dev = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except:
    is_dev = False
is_prod = not is_dev
debug = is_dev

tzinfo = timezone.Pacific
jquery = '//ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js'
jquery_ui = '//ajax.googleapis.com/ajax/libs/jqueryui/1.8.0/jquery-ui.min.js'
reset_css = '//developer.yahoo.com/yui/build/reset/reset.css'
favicon = '//images.yelp.com/favicon.ico'
hostname = 'yelp-pushmaster.appspot.com' if is_prod else 'localhost:8080'
protocol = 'http'
static_host_count = 4
mail_host = 'yelp-pushmaster.appspotmail.com'

# Certain private configuration options are stored in the datastore
datastore_config = ConfigModel.all().order('-timestamp').get()
mail_domain = datastore_config.mail_domain
mail_sender = datastore_config.mail_sender + mail_domain
mail_to = datastore_config.mail_to + mail_domain
mail_request = datastore_config.mail_request + mail_domain
push_plans_url = datastore_config.push_plans_url
git_branch_url = datastore_config.git_branch_url


def url(path):
    return '%s://%s%s' % (protocol, hostname, path)

def static_host(path):
    return '%d.%s' % (hash(path) % static_host_count, hostname)

nothing_messages = (
    'Zip.',
    'Zero.',
    'Zilch.',
    'Nada.',
    'Bupkiss.',
    'Nothing to see here, move along.',
    'Nope.',
    'Void.',
    'None.',
    'Naught.',
    'This area left intentionally blank.',
    'Diddly.',
    'Nix.',
    'Nothing.',
    'Zippo.',
    'Zot.',
    'Null.',
    'Nil.',
    'Crickets.',
    'Empty.',
    'Tumbleweeds.',
    'A cricket riding a tumbleweed.',
    'The sound of one hand clapping.',
    'Guru Meditation #00000004 0000AAC0',
    )
