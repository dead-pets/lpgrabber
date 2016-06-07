import json
import logging
import re

from cliff.command import Command

from lpgrabber.boards.dumbboard import DumbBoard
from lpgrabber.boardsync import BoardSync
from lpgrabber.bugtrackers.dumbtracker import DumbTracker
from lpgrabber.exceptions import CommandError
from lpgrabber.utils.trello import get_trello_board


class TrelloSync(Command):
    """Update trello board from launchpad filters"""

    log = logging.getLogger(__name__)
    bugtracker_driver = DumbTracker
    board_driver = DumbBoard
    boardsync_driver = BoardSync

    def get_parser(self, prog_name):
        parser = super(TrelloSync, self).get_parser(prog_name)
        self.bugtracker_driver.update_argparse(parser)
        self.board_driver.update_argparse(parser)
        self.boardsync_driver.update_argparse(parser)
        return parser

    def take_action(self, parsed_args):
        err_count = 0
        logging.getLogger("requests").setLevel(logging.WARNING)
        self.log.info('Connecting to Launchpad')
        try:
            self.board = get_trello_board(self.tr, parsed_args.board, True)
        except IndexError:
            raise CommandError(
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
            # TODO(dpyzhov): try to replace several cycles with one izip
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

    def proceed_task(self, task):
        self.log.debug("Processing task {0}".format(task))
        bug = task.bug
        card_list = self.get_task_list(task)
        if str(bug.id) not in self.cards:
            self.log.debug("Creating card for bug {0}".format(bug.id))
            card = card_list.add_card(
                self.get_card_title(task),
                self.get_card_description(task, card_list))
            self.cards[str(bug.id)] = card
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
