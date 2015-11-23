import json
import logging
import re

from cliff.command import Command
from launchpadlib.launchpad import Launchpad
from pygerrit.rest import GerritRestAPI
from trello import TrelloClient


class TrelloCmd(Command):
    "Update trello board from launchpad filters"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(TrelloCmd, self).get_parser(prog_name)
        parser.add_argument(
            '--filter', type=str, action='append', required=True,
            help="List of params for searchTasks",
        )
        parser.add_argument(
            '--project', type=str, action='append', required=True,
            help="Project"
        )
        parser.add_argument(
            '--board', type=str, required=True,
            help="Trello board name"
        )
        parser.add_argument(
            '--trello-key', type=str, required=False,
            help="You can get one at https://trello.com/app-key"
        )
        parser.add_argument(
            '--trello-secret', type=str, required=False,
            help="You can get one at https://trello.com/app-key"
        )
        parser.add_argument(
            '--trello-token', type=str, required=False,
            help="You can get one at https://trello.com/1/connect?" +
                 "key=YOUR_TRELLO_KEY&name=bugfix-app&response_type=token&" +
                 "scope=read,write&expiration=never"
        )
        parser.add_argument(
            '--trello-token-secret', type=str, required=False,
        )
        parser.add_argument(
            '--create-board', action='store_true',
            help='Create Trello board if not exists'
        )
        parser.add_argument(
            '--use-labels', nargs='+',
            help='Labels for cards', default=[
                # 'area-library', 'area-python',
                # 'team-bugfix',
                # 'team-enhancements', 'team-network', 'team-upgrades',
                'swarm-blocker', 'sla1', 'sla2', 'tricky',
                'low-hanging-fruit', 'tech-debt'
            ]
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('connecting to Launchpad')
        self.lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')
        self.tr = TrelloClient(
            api_key=parsed_args.trello_key,
            api_secret=parsed_args.trello_secret,
            token=parsed_args.trello_token,
            token_secret=parsed_args.trello_token_secret)
        self.log.debug(self.tr.list_boards())
        try:
            self.board = [
                board for board in self.tr.list_boards()
                if board.name == parsed_args.board
            ][0]
        except IndexError:
            if parsed_args.create_board:
                self.board = self.tr.add_board(parsed_args.board)
                # for label in self.board.all_lists():
                #    #label.delete()
                #    #                    self.client.fetch_json(
                #    #            '/cards/' + self.id,
                #    #            http_method='DELETE')
                for list in self.board.open_lists():
                    list.close()
            else:
                raise Exception(
                    "Board {0} doesn't exist. Use --create-board argument" +
                    " in order to create it".format(parsed_args.board))
        self.log.debug(self.board)
        self.tag_labels = parsed_args.use_labels
        self.cards = dict()
        self.untouched_cards = dict()
        for card in self.board.open_cards():
            groups = re.search('(\d+)', card.name)
            if not (groups is None):
                bug_id = groups.group(0)
                if bug_id not in self.cards:
                    self.untouched_cards[bug_id] = card
                    self.log.debug(
                        "Found existing card for bug {0}".format(bug_id))
                    self.cards[bug_id] = card
                else:
                    self.log.info(
                        "Killing duplicate card for bug {0}".format(bug_id))
                    card.delete()

        for prj_name in parsed_args.project:
            prj = self.lp.projects[prj_name]
            for f in parsed_args.filter:
                self.log.debug(f)
                filt = json.loads(f)
                if filt['milestone']:
                    filt['milestone'] = prj.getMilestone(
                        name=filt['milestone'])
                if 'assignee' in filt:
                    filt['assignee'] = self.lp.people[filt['assignee']]
                self.log.debug(filt)
                for task in prj.searchTasks(**filt):
                    self.proceed_task(task)
                for series in prj.series:
                    self.log.debug(str(prj.name) + ":" + str(series.name))
                    for task in series.searchTasks(**filt):
                        self.proceed_task(task)

        if self.untouched_cards:
            try:
                out_of_scope_list = [
                    list for list in self.board.open_lists()
                    if list.name == 'Trash/Out of scope'][0]
            except IndexError:
                out_of_scope_list = self.board.add_list('Trash/Out of scope')
            for card in self.untouched_cards.values():
                card.change_list(out_of_scope_list.id)

    def get_task_reviews(self, task):
        self.log.debug("Searching for reviews for task {0}".format(task))
        bug = task.bug
        gerrits = [
            'https://review.openstack.org/', 'https://review.fuel-infra.org/']
        reviews = []
        # Message number 0 is description
        is_description = True
        for msg in bug.messages:
            if is_description:
                is_description = False
                continue
            for g in gerrits:
                reviews += re.findall(g + '\d+', msg.content)
                long_reviews = re.findall(g + '#/c/\d+/', msg.content)
                for u in long_reviews:
                    reviews += [u.replace('#/c/', '').rstrip('/')]
        open_reviews = []
        for rev_url in set(reviews):
            [base_url, id] = rev_url.rsplit('/', 1)
            rest = GerritRestAPI(base_url)
            try:
                review = rest.get('/changes/' + id)
                if review['status'] == 'NEW':
                    open_reviews.append(rev_url)
                    self.log.debug("Found open review {0}".format(rev_url))
            except Exception:
                pass

        return open_reviews

    def get_task_list(self, task):
        list_name = 'Bad Status'
        try:
            if task.status in ['Confirmed']:
                if task.assignee is None or task.assignee.is_team:
                    list_name = 'Inbox/Need triage'
                else:
                    list_name = 'Assigned/Investigating'
            if task.status in ['Incomplete']:
                list_name = 'Incomplete/Need more info'
            if task.status in ['Triaged']:
                list_name = 'Triaged/Ready to be fixed'
            if task.status in ['In Progress']:
                if self.get_task_reviews(task):
                    list_name = 'In Progress/Need review'
                else:
                    list_name = 'In Progress/Working on fix'
            if task.status in ['Fix Committed', 'Fix Released']:
                list_name = 'Fix Committed/Done'
            if task.status in ['Invalid', 'Opinion', 'Won\'t Fix']:
                list_name = 'Won\'t Fix/Done'
            if (
                not filter(lambda x: x.startswith('area-'), task.bug.tags) or
                task.status in ['New']
            ):
                list_name = 'New/Need confirmation'
            # if (
            #     not filter(lambda x: x.startswith('team-'), task.bug.tags)
            #     and 'tech-debt' not in task.bug.tags and
            #     task.status in [
            #         'New', 'Confirmed', 'Triaged', 'In Progress',
            #         'Incomplete']
            #     ):
            #     list_name = 'New/Need confirmation'
            if 'blocked' in task.bug.tags:
                list_name = 'Blocked/On hold'
            return [
                list for list in self.board.open_lists()
                if list.name == list_name][0]
        except IndexError:
            return self.board.add_list(list_name)

    def get_task_labels(self, task):
        bug = task.bug
        tags = list(set(bug.tags).intersection(self.tag_labels))
        # Each bug should have either team tag or no-team tag or tech-debt tag
        team_tags = filter(lambda x: x.startswith('team-'), bug.tags)
        if team_tags:
            tags += team_tags
        else:
            if 'tech-debt' not in bug.tags:
                tags += ['no-team']
        # if task.importance in ['Critical', 'High']:
        #     tags.append('high-priority')
        return tags

    def proceed_task(self, task):
        self.log.debug("Processing task {0}".format(task))
        bug = task.bug
        if str(bug.id) not in self.cards:
            self.log.debug("Creating card for bug {0}".format(bug.id))
            card = self.get_task_list(task).add_card(
                'Bug {0}: {1}'.format(bug.id, bug.title),
                bug.web_link + '\n' + bug.description)
            self.cards[bug.id] = card
        else:
            self.log.debug("Getting card for task {0}".format(task))
            card = self.cards[str(bug.id)]
            try:
                del self.untouched_cards[str(bug.id)]
            except KeyError:
                pass
            new_list = self.get_task_list(task)
            self.log.debug(
                "Updating existing card for bug {0}," +
                " moving to {1} list".format(bug.id, new_list))
            card.change_list(self.get_task_list(task).id)
        for label_name in self.get_task_labels(task):
            try:
                label = [
                    l for l in self.board.get_labels()
                    if l.name == label_name][0]
            except IndexError:
                label = self.board.add_label(label_name, 'green')
            try:
                card.add_label(label)
            except Exception:
                pass
        self.log.debug(task)

"""
for task in tasks:
        bug = task.bug
        bug_id = str(bug.id)
        print 'LP bug', bug_id #, bug.title, task.status, task.assignee
        try:
            username = task.assignee.name
        except:
            username = 'ashtokolov'
        lp_member_id = lp2tr(username)
        if not (bug_id in bugs):
            print 'Add to trello:', bug_id
            card = list_new.add_card('Bug '+bug_id+': '+task.bug.title,
                bug.web_link+'\n'+bug.description)
            card.client.fetch_json('/cards/{0}/idMembers'.format(card.id),
                http_method='PUT',
                post_args={'value': '{0}'.format(lp_member_id)})
            card.client.fetch_json('/cards/{0}/labels'.format(card.id),
                http_method='PUT',
                post_args={'value': IMP_2_LABEL[task.importance]})
        else:
            card = bugs[bug_id]
            try:
                tr_member_id = card.member_id
            except:
                tr_member_id = "ashtokolov"
            if card.desc != bug.web_link+'\n'+bug.description:
                card.client.fetch_json('/cards/{0}/desc'.format(card.id),
                    http_method='PUT',
                    post_args={'value': bug.web_link+'\n'+bug.description})
            if lp_member_id != tr_member_id[0] or len(tr_member_id) >= 2:
                print 'LP assignee differs'
                card.client.fetch_json('/cards/{0}/idMembers'.format(card.id),
                    http_method='PUT',
                    post_args={'value': '{0}'.format(lp_member_id)})
            if card.labels[0]['color'] != IMP_2_LABEL[task.importance]:
                card.client.fetch_json('/cards/{0}/labels'.format(card.id),
                    http_method='PUT',
                    post_args={'value': IMP_2_LABEL[task.importance]})
"""
