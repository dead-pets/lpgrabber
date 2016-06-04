from unittest import skip
from unittest import TestCase

from lpgrabber.trellostats import get_trello_list_type


class TestGet_list_type(TestCase):
    @skip
    def test_dummy(self):
        self.assertEqual(get_trello_list_type({'name': 'New'}), 'open')
