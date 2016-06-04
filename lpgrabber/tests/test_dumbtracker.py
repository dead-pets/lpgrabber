# from unittest import skip
from unittest import TestCase

from lpgrabber.bugtrackers.dumbtracker import DumbTracker
from lpgrabber.bugtrackers.dumbtracker import DumbTrackerTask


class TestDumbTracker(TestCase):
    def test_add_task(self):
        tracker = DumbTracker()
        tracker.add_or_replace_task(5, "Task 5")
        self.assertIsInstance(tracker.tasks[5], DumbTrackerTask)
        self.assertEqual(tracker.tasks[5].title, "Task 5")

    def test_replace_task(self):
        tracker = DumbTracker()
        tracker.add_or_replace_task(5, "Task 5")
        tracker.add_or_replace_task(5, "Task 5 updated")
        self.assertEqual(len(tracker.tasks), 1)
        self.assertIsInstance(tracker.tasks[5], DumbTrackerTask)
        self.assertEqual(tracker.tasks[5].title, "Task 5 updated")

    def test_list_tasks(self):
        tracker = DumbTracker()
        tracker.add_or_replace_task(5, "Task 5")
        tracker.add_or_replace_task(10, "Task 10")
        tracker.add_or_replace_task(15, "Task 15")
        tracker.add_or_replace_task(20, "Task 20")
        elems = [x for x in tracker.iter()]
        self.assertEqual(len(elems), 4)
