from trello import TrelloClient


class TrelloBoard(object):
    def __init__(self, parsed_args):
        self.tr = TrelloClient(
            api_key=parsed_args.trello_key,
            api_secret=parsed_args.trello_secret,
            token=parsed_args.trello_token,
            token_secret=parsed_args.trello_token_secret
        )

    @classmethod
    def update_argparse(cls, parser):
        parser.add_argument(
            '--board', type=str, required=True,
            help="Trello board name"
        )
        parser.add_argument(
            '--create-board', action='store_true',
            help='Create Trello board if not exists'
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


class TrelloBoardCard(object):
    def calc_trello_title(self):
        return u'Bug {0} ({1}): {2}'.format(
            self.id, self.assignee, self.title
        )[:200]
