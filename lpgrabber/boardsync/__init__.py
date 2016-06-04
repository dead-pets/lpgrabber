class BoardSync(object):
    def __init__(self, tracker, board):
        self.tracker = tracker
        self.board = board

    def sync(self, convert_task_to_card):
        for task in self.tracker.tasks.values():
            self.board.clone_card(convert_task_to_card(task))
