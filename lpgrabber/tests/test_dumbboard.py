from unittest import skip
from unittest import TestCase

from lpgrabber.boards.dumbboard import DumbBoard
from lpgrabber.boards.dumbboard import DumbBoardCard


class TestDumbBoard(TestCase):
    def test_create(self):
        board = DumbBoard(name="Dumb board")
        self.assertIsInstance(board, DumbBoard)
        self.assertEqual(board.name, "Dumb board")
        self.assertEqual(board.cards, {})

    def test_add_card(self):
        board = DumbBoard(name="Dumb board")
        board.add_or_replace_card(id=5, title="Test card")
        card = board.get_card(id=5)
        self.assertIsInstance(card, DumbBoardCard)
        self.assertEqual(card.id, 5)

    def test_add_two_cards(self):
        board = DumbBoard(name="Dumb board")
        board.add_or_replace_card(id=5, title="Test card 5")
        board.add_or_replace_card(id=9, title="Test card 9")
        card1 = board.get_card(id=5)
        card2 = board.get_card(id=5)
        self.assertIsInstance(card1, DumbBoardCard)
        self.assertEqual(card1.id, 5)
        self.assertEqual(card1.title, "Test card 5")
        self.assertIsInstance(card2, DumbBoardCard)
        self.assertEqual(card2.id, 5)
        self.assertEqual(card2.title, "Test card 5")

    def test_clone(self):
        board = DumbBoard(name="Dumb board")
        card = DumbBoardCard(id=5, title="Card 5")
        board.clone_card(card)
        card.title = "Card 5 updated"
        self.assertIsInstance(board.cards[5], DumbBoardCard)
        self.assertEqual(card.title, "Card 5 updated")
        self.assertEqual(board.cards[5].title, "Card 5")

    @skip
    def test_non_existing_board(self):
        pass

    @skip
    def test_non_existing_card(self):
        pass

    @skip
    def test_argparse_params(self):
        self.fail("Test not implemented yet")
