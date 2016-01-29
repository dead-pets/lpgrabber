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
                'tricky', 'low-hanging-fruit', 'tech-debt'
            ]
        )
        return parser

    def take_action(self, parsed_args):
        err_count = 0
        logging.getLogger("requests").setLevel(logging.WARNING)
        self.log.info('Connecting to Launchpad')
        self.lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')
        self.tr = TrelloClient(
            api_key=parsed_args.trello_key,
            api_secret=parsed_args.trello_secret,
            token=parsed_args.trello_token,
            token_secret=parsed_args.trello_token_secret)
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
        self.log.info("Working with board {0}".format(self.board))
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
        self.log.info("Found {0} existing cards".format(
            len(self.untouched_cards)))

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
                if 'status' not in filt:
                    filt['status'] = [
                        'New', 'Incomplete', 'Opinion', 'Invalid',
                        'Won\'t Fix', 'Expired', 'Confirmed', 'Triaged',
                        'In Progress', 'Fix Committed', 'Fix Released'
                    ]
                self.log.debug(filt)
                self.log.info("Searching for tasks in project %s" % prj_name)
                for task in prj.searchTasks(**filt):
                    self.log.info("Proceeding task %s" % task)
                    retries = 3
                    for i in range(retries):
                        try:
                            self.proceed_task(task)
                        except Exception as e:
                            if i < retries:
                                self.log.exception(e)
                                self.log.warning(
                                    "Got an exception for task %s, retrying"
                                    % task)
                                continue
                            else:
                                self.log.exception(e)
                                self.log.warning(
                                    "Failed to proceed task %s" % task)
                                err_count += 1
                        break
                for series in prj.series:
                    self.log.info("Searching for tasks in {0}:{1}".format(
                        str(prj.name), str(series.name)))
                    for task in series.searchTasks(**filt):
                        self.log.info("Proceeding task %s" % task)
                        retries = 3
                        for i in range(retries):
                            try:
                                self.proceed_task(task)
                            except Exception as e:
                                if i < retries:
                                    continue
                                else:
                                    self.log.exception(e)
                                    self.log.warning(
                                        "Failed to proceed task %s" % task)
                                    err_count += 1
                            break

        if self.untouched_cards:
            self.log.info("%d cards are out of scope" % len(
                self.untouched_cards))
            try:
                out_of_scope_list = [
                    list for list in self.board.open_lists()
                    if list.name == 'Trash/Out of scope'][0]
            except IndexError:
                out_of_scope_list = self.board.add_list('Trash/Out of scope')
            for card in self.untouched_cards.values():
                card.change_list(out_of_scope_list.id)

        self.log.info("Finished with %d errors" % err_count)
        if err_count > 0:
            return 1
        return 0

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
                long_reviews = re.findall(g + '#/c/\d+', msg.content)
                for u in long_reviews:
                    reviews += [u.replace('#/c/', '')]
        open_reviews = []
        for rev_url in set(reviews):
            [base_url, id] = rev_url.rsplit('/', 1)
            rest = GerritRestAPI(base_url)
            try:
                review = rest.get('/changes/{0}/detail'.format(id))
                if review['status'] == 'NEW':
                    status = []
                    if 'rejected' in review['labels']['Workflow']:
                        status.append('WIP')
                    if 'disliked' in review['labels']['Verified']:
                        status.append('FAIL')
                    open_reviews.append({'url': rev_url, 'status': status})
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
            if task.status in ['New']:
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
        if not filter(lambda x: x.startswith('area-'), task.bug.tags):
            tags += ['no-area']
        # if task.importance in ['Critical', 'High']:
        #     tags.append('high-priority')
        return tags

    def get_card_title(self, task):
        bug = task.bug
        assignee_id = "unassigned"
        if task.assignee_link is not None:
            assignee_id = task.assignee_link.split('~')[-1]
        return u'Bug {0} ({1}): {2}'.format(
            bug.id, assignee_id, bug.title)[:200]

    def get_card_description(self, task, card_list):
        bug = task.bug
        desc = "Created by {0}\n".format(bug.owner_link.split('~')[-1])
        desc += bug.web_link + "\n"
        if card_list.name == 'In Progress/Need review':
            desc += "Reviews:\n" + "\n".join(map(
                lambda x: u"{0} {1}".format(x['url'], ':'.join(x['status'])),
                self.get_task_reviews(task)
            )) + "\n"
        desc += "\n----------\n" + bug.description
        return desc[:1000]

    def proceed_task(self, task):
        self.log.debug("Processing task {0}".format(task))
        bug = task.bug
        card_list = self.get_task_list(task)
        if str(bug.id) not in self.cards:
            self.log.debug("Creating card for bug {0}".format(bug.id))
            card = card_list.add_card(
                self.get_card_title(task),
                self.get_card_description(task, card_list))
            self.cards[bug.id] = card
        else:
            self.log.debug("Getting card for task {0}".format(task))
            card = self.cards[str(bug.id)]
            try:
                del self.untouched_cards[str(bug.id)]
            except KeyError:
                pass
            self.log.debug(
                (
                    "Updating existing card for bug {0}, moving to {1} list"
                ).format(bug.id, card_list))
            card.change_list(card_list.id)
            new_name = self.get_card_title(task)
            if new_name != card.name.decode('utf-8'):
                card.set_name(new_name)
            new_desc = self.get_card_description(task, card_list)
            if new_desc != card.description:
                card.set_description(new_desc)
        tags = self.get_task_labels(task)
        for label in card.labels:
            if label.name not in tags:
                # delete_label is not published on pypi yet
                # card.delete_label(label)
                card.client.fetch_json(
                    '/cards/' + card.id + '/idLabels/' + label.id,
                    http_method='DELETE')
        for label_name in tags:
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
