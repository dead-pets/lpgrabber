from trello import TrelloClient


class TrelloBoard(object):
    def __init__(self, parsed_args):
        self.tr = TrelloClient(
            api_key=parsed_args.trello_key,
            api_secret=parsed_args.trello_secret,
            token=parsed_args.trello_token,
            token_secret=parsed_args.trello_token_secret
        )


class TrelloBoardCard(object):
    def calc_trello_title(self):
        return u'Bug {0} ({1}): {2}'.format(
            self.id, self.assignee, self.title
        )[:200]
