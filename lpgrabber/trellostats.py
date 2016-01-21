import logging

from cliff.command import Command
from trello import TrelloClient


class TrelloStats(Command):
    "Get board statistics from trello"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(TrelloStats, self).get_parser(prog_name)
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
        return parser

    def take_action(self, parsed_args):
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
            raise Exception(
                "Board {0} doesn't exist".format(parsed_args.board))
        self.log.debug(self.board)

        def get_card_type(card):
            l_names = [l.name for l in card.labels]
            if 'tech-debt' in l_names:
                return 'tech-debt'
            return 'bug'

        def get_list_type(list):
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

        stats = [
            get_card_type(c) + ":" + get_list_type(c.get_list())
            for c in self.board.open_cards()
        ]
        for s in sorted(set(stats)):
            self.log.info("{0}: {1}".format(s, stats.count(s)))
