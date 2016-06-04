class DumbTracker(object):
    def __init__(self):
        self.tasks = {}

    def add_or_replace_task(self, id, title):
        self.tasks[id] = DumbTrackerTask(id, title)

    def iter(self):
        for t in self.tasks:
            yield t


class DumbTrackerTask(object):
    def __init__(self, id, title, status='New', assignee=None):
        self.id = id
        self.title = title
        self.status = status
        self.assignee = assignee
