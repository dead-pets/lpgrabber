import logging

from cliff.command import Command
from launchpadlib.launchpad import Launchpad


class KillDupes(Command):
    "Update trello board from launchpad filters"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(KillDupes, self).get_parser(prog_name)
        parser.add_argument(
            '--open-only', action='store_true',
            help='Work only with open bugs'
        )
        parser.add_argument(
            '--next-series', type=str,
            help='Do not remove development focus series from bugs that ' +
            'are targeted to the next series'
        )
        parser.add_argument(
            '--dont-delete', action='store_true',
            help='Don\t delete series task, only update root task'
        )
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            'project', type=str, help='Project name', nargs='+')
        return parser

    def take_action(self, parsed_args):
        def task_status(bt):
            if bt.milestone:
                milestone_name = str(bt.milestone).split('/')[6]
            else:
                milestone_name = 'None'
            if bt.assignee:
                assignee_name = str(bt.assignee).split('~')[1]
            else:
                assignee_name = 'None'
            return (
                (
                    "status: {0}, importance: {1}, " +
                    "milestone: {2}, assignee: {3}"
                ).format(
                    bt.status, bt.importance,
                    milestone_name,
                    assignee_name))
        self.log.debug('connecting to Launchpad')
        lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')
        if parsed_args.open_only:
            search_states = [
                'Incomplete', 'Confirmed', 'Triaged', 'In Progress',
                'Incomplete'
            ]
        else:
            search_states = [
                'New', 'Incomplete', 'Confirmed', 'Triaged', 'In Progress',
                'Incomplete', 'Opinion', 'Invalid', 'Won\'t Fix', 'Expired',
                'Fix Committed', 'Fix Released'
            ]
        for prj_name in parsed_args.project:
            self.log.debug("Searching for tasks in project {0}".format(
                prj_name))
            prj = lp.projects[prj_name]
            dev_focus = prj.development_focus
            next_focus = None
            if parsed_args.next_series:
                next_focus = prj.getSeries(name=parsed_args.next_series)

            collection = dev_focus.searchTasks(status=search_states)
            for bug_task in collection:
                bug = bug_task.bug
                bt_0 = bug.bug_tasks[0]
                bt_dev = None
                bt_next = None
                for bt in bug.bug_tasks:
                    if bt.target == prj:
                        bt_0 = bt
                    if bt.target == dev_focus:
                        bt_dev = bt
                    if bt.target == next_focus:
                        bt_next = bt
                self.log.debug("Bug link: " + bug.web_link)
                self.log.debug("Default task: {0}".format(task_status(bt_0)))
                self.log.debug("Development focus task: {0}".format(
                    task_status(bt_dev)))
                if bt_next:
                    self.log.debug("Next focus task: {0}".format(
                        task_status(bt_next)))
                if bt_0.target != prj:
                    raise Exception(
                        "Default task for bug #{0} is from project {1}".format(
                            bug.id, bt_0.target.name
                        ))
                if bt_dev.target != dev_focus:
                    raise Exception("Dev focus task has wrong target")
                if bt_next:
                    if (
                        bt_0.status != bt_next.status or
                        bt_0.importance != bt_next.importance or
                        bt_0.milestone != bt_next.milestone or
                        bt_0.assignee != bt_next.assignee
                    ):
                        self.log.debug(
                            "Replacing default task with next focus data")
                        if not parsed_args.dry_run:
                            [
                                bt_0.status, bt_0.importance,
                                bt_0.milestone, bt_0.assignee
                            ] = [
                                bt_next.status, bt_next.importance,
                                bt_next.milestone, bt_next.assignee
                            ]
                            bt_0.lp_save()
                    else:
                        self.log.debug("Default task is actual")
                    self.log.debug("Leaving dev focus task as is")
                else:
                    if (
                        bt_0.status != bt_dev.status or
                        bt_0.importance != bt_dev.importance or
                        bt_0.milestone != bt_dev.milestone or
                        bt_0.assignee != bt_dev.assignee
                    ):
                        self.log.debug(
                            "Replacing default task with dev focus task")
                        if not parsed_args.dry_run:
                            [
                                bt_0.status, bt_0.importance,
                                bt_0.milestone, bt_0.assignee
                            ] = [
                                bt_dev.status, bt_dev.importance,
                                bt_dev.milestone, bt_dev.assignee
                            ]
                            bt_0.lp_save()
                    else:
                        self.log.debug("Default task is actual")
                    if not parsed_args.dont_delete:
                        self.log.debug("Removing development focus task")
                        if not parsed_args.dry_run:
                            bt_dev.lp_delete()
        return 0
