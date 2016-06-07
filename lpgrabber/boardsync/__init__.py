class BoardSync(object):
    def __init__(self, tracker, board):
        self.tracker = tracker
        self.board = board

    def sync(self, convert_task_to_card):
        for task in self.tracker.tasks.values():
            self.board.clone_card(convert_task_to_card(task))

    @classmethod
    def update_argparse(cls, parser):
        parser.add_argument(
            '--use-labels', nargs='+',
            help='Labels for cards', default=[
                'tricky', 'low-hanging-fruit', 'tech-debt'
            ]
        )
        return parser
