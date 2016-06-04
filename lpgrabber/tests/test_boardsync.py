# from unittest import skip
from unittest import TestCase

from lpgrabber.boards.dumbboard import DumbBoard
from lpgrabber.boards.dumbboard import DumbBoardCard
from lpgrabber.boardsync import BoardSync
from lpgrabber.bugtrackers.dumbtracker import DumbTracker


class TestBoardSync(TestCase):
    def test_dumb_sync(self):
        tracker = DumbTracker()
        board = DumbBoard(name="Dumb")
        tracker.add_or_replace_task(5, "Task 5")
        bs = BoardSync(tracker, board)
        bs.sync(dumb_convert_task_to_card)
        self.assertIsInstance(bs, BoardSync)
        self.assertEqual(board.cards[5].title, "Task 5")
        self.assertEqual(board.cards[5].status, "Inbox")


def dumb_convert_task_to_card(task):
    return DumbBoardCard(
        id=task.id, title=task.title, status="Inbox",
        assignee=task.assignee
    )
