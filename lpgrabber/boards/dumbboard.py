import copy


class DumbBoard(object):
    def __init__(self, name):
        self.name = name
        self.cards = {}

    def add_or_replace_card(self, id, title):
        self.cards[id] = DumbBoardCard(id, title)

    def clone_card(self, card):
        self.cards[card.id] = copy.deepcopy(card)

    def get_card(self, id):
        return self.cards[id]

    @classmethod
    def update_argparse(cls, parser):
        return parser


class DumbBoardCard(object):
    def __init__(self, id, title, status='New', assignee=None):
        self.id = id
        self.title = title
        self.status = status
        self.assignee = assignee
