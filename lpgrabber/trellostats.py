import logging
import time

from cliff.command import Command
from trello import TrelloClient

from lpgrabber.exceptions import CommandError
from lpgrabber.utils.trello import add_trello_auth_arguments
from lpgrabber.utils.trello import get_trello_board


class TrelloStats(Command):
    """Count bugs of every type in every column type"""
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(TrelloStats, self).get_parser(prog_name)
        parser.add_argument(
            '--board', type=str, required=True,
            help="Trello board name"
        )
        return add_trello_auth_arguments(parser)

    def take_action(self, parsed_args):
        logging.getLogger("requests").setLevel(logging.WARNING)
        self.log.info("Stats for %s" % time.strftime("%c"))
        client = TrelloClient(
            api_key=parsed_args.trello_key,
            api_secret=parsed_args.trello_secret,
            token=parsed_args.trello_token,
            token_secret=parsed_args.trello_token_secret)
        try:
            board = get_trello_board(client, parsed_args.board)
        except IndexError:
            raise CommandError(
                "Board {0} doesn't exist".format(parsed_args.board))
        self.log.debug(board)
        stats_records = [
            (
                get_trello_card_type(card) + ":" +
                get_trello_list_type(card.get_list())
            )
            for card in board.open_cards()
            ]
        for record in sorted(set(stats_records)):
            self.log.info(
                "{0}: {1}".format(record, stats_records.count(record))
            )


def get_trello_card_type(card):
    l_names = [l.name for l in card.labels]
    if 'tech-debt' in l_names:
        return 'tech-debt'
    return 'bug'


def get_trello_list_type(list):
    if (
        'New' in list.name or
        'Inbox' in list.name or
        'Assigned' in list.name or
        'Triaged' in list.name or
        'Blocked' in list.name
    ):
        return 'open'
    if (
        'In Progress' in list.name
    ):
        return 'in progress'
    if 'Fix Committed' in list.name:
        return 'done'
    if (
        'Incomplete' in list.name or
        'Won\'t Fix' in list.name or
        'Trash' in list.name
    ):
        return 'rejected'
    return 'unknown'
