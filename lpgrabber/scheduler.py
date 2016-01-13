from launchpadlib.launchpad import Launchpad
from multiprocessing import JoinableQueue
from multiprocessing import Process
from time import sleep


class Scheduler(object):
    def worker(self):
        lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')
        for item in iter(self.input_queue.get, None):
            if item is None:
                break
            for i in xrange(3):
                try:
                    r = self.command(lp=lp, item=item)
                except Exception:
                    sleep(0.5)
                    continue
                break
            if 'r' in vars():
                self.output_queue.put(r)
            self.input_queue.task_done()
        self.input_queue.task_done()

    def run(self, command, queue, processes=10):
        self.input_queue = JoinableQueue()
        self.output_queue = JoinableQueue()
        self.command = command
        procs = []
        for x in xrange(processes):
            procs.append(Process(target=self.worker))
            procs[-1].daemon = True
            procs[-1].start()

        for elem in queue:
            self.input_queue.put(elem)

        self.input_queue.join()

        for x in xrange(processes):
            self.input_queue.put(None)

        for x in xrange(processes):
            procs[x].join()

        result = []
        while not self.output_queue.empty():
            result.append(self.output_queue.get())
        return result
