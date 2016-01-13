from datetime import datetime
from datetime import timedelta
from time import sleep
import unittest

from lpgrabber.scheduler import Scheduler


class FakeTest(unittest.TestCase):
    def test_success(self):
        self.assertTrue(True)

    @unittest.skip("Skipping broken demo test")
    def test_failure(self):
        self.assertTrue(False)


class TestCache(unittest.TestCase):
    pass


class TestScheduler(unittest.TestCase):
    workers = 2
    work_time = 1
    elems = 4

    def worker(self, lp, item):
        sleep(self.work_time)
        return item + 1

    def failing_worker(self, lp, item):
        if self.worker_fail:
            raise Exception("Failed intentionally")
        return item + 1

    def once_failing_worker(self, lp, item):
        if self.worker_fail:
            self.worker_fail = False
            raise Exception("Failed intentionally")
        return item + 1

    def test_parallel(self):
        start = datetime.today()
        r = Scheduler().run(
            command=self.worker,
            queue=range(self.elems),
            processes=self.workers)
        end = datetime.today()
        self.assertEqual(sum(r), (self.elems + 1) * self.elems / 2)
        self.assertLess(
            end - start,
            timedelta(seconds=(self.work_time * self.elems)))

    def test_failures(self):
        self.worker_fail = True
        r = Scheduler().run(
            command=self.failing_worker,
            queue=range(self.elems),
            processes=1
        )
        self.assertEqual(r, [])

    def test_temporary_failure(self):
        self.worker_fail = True
        r = Scheduler().run(
            command=self.once_failing_worker,
            queue=range(self.elems),
            processes=1
        )
        self.assertEqual(sum(r), (self.elems + 1) * self.elems / 2)
