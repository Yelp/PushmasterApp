import datetime, httplib, logging

from google.appengine.api import users

from pushmaster import config, model, query, timezone, urls, logic
from pushmaster.view import common, RequestHandler
from pushmaster.taglib import T

def report_date_range(datestr):
    from_date = datetime.datetime.strptime(datestr, '%Y%m%d').replace(tzinfo=config.tzinfo)
    to_date = from_date + datetime.timedelta(days=6)
    return (from_date, to_date)

def last_monday_datetime(from_date=None):
    from_date = from_date or datetime.date.today()
    return from_date - datetime.timedelta(days=from_date.weekday())

class LastWeek(RequestHandler):
    def get(self, datestr=None):
        if datestr:
            from_date, to_date = report_date_range(datestr)
        else:
            for_date = last_monday_datetime() - datetime.timedelta(days=7)
            return self.redirect('/lastweek/' + for_date.strftime('%Y%m%d'))

        pushes = query.pushes_for_the_week_of(from_date)
        requests = []
        for push in pushes:
            requests.extend(query.push_requests(push))
        requests = sorted(requests, key=lambda r: r.mtime)

        doc = common.Document(title='pushmaster: weekly report: ' + datestr)

        teams_list = T.ul(class_='teams')
        doc(teams_list)

        nothing_messages_list = None

        report_users = query.report_users_by_team()
        for (team_name, team) in sorted(report_users.iteritems()):
            team_item = T.li(class_='team')(T.h3(team_name))
            teams_list(team_item)

            devs_list = T.ul(class_='devs')
            team_item(devs_list)
            for dev in sorted(team['dev']):
                dev_item = T.li(class_='dev')(T.h4(logic.user_info(users.User('@'.join([dev, config.mail_domain]))).full_name))
                devs_list(dev_item)
                dev_requests = filter(lambda r: r.owner.nickname() == dev, requests)
                if dev_requests:
                    requests_list = T.ol(class_='requests')(map(common.request_item, dev_requests))
                    dev_item(requests_list)
                else:
                    # lazy (re)initialize random messages
                    if not nothing_messages_list:
                        nothing_messages_list = list(config.nothing_messages)
                        import random
                        random.shuffle(nothing_messages_list)

                    dev_item(T.div(nothing_messages_list.pop(), class_='nothing'))


            if 'prod' in team:
                pm_title ='PM: ' if len(team['prod']) == 1 else 'PMs: '
                pm_names = ', '.join([logic.user_info(users.User('@'.join([pm, config.mail_domain]))).full_name for pm in team['prod']])
                team_item(T.h4(pm_title, pm_names, class_='pm'))
        
        doc.serialize(self.response.out)
