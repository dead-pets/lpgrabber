import logging

import argparse
from cliff.command import Command
from launchpadlib.launchpad import Launchpad
import pandas as pd


class Bugs(Command):
    "Download bugs data."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Bugs, self).get_parser(prog_name)
        parser.add_argument(
            '-m', '--milestone', type=str,
            help='Grab only bugs targeted to some milestone')
        parser.add_argument(
            '--updated-since', type=str, help='Grab only new bugs')
        parser.add_argument(
            '--open-only', action='store_true', help='Grab only open bugs')
        parser.add_argument(
            '--base-csv', type=argparse.FileType('r'),
            help='Data from previous run')
        parser.add_argument(
            '--outfile', type=argparse.FileType('w'), default='bugs.csv',
            help='Report destination')
        parser.add_argument('project', type=str, help='Project name')
        return parser

    def take_action(self, parsed_args):
        self.log.debug('connecting to Launchpad')
        lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')
        prj = lp.projects[parsed_args.project]
        if parsed_args.milestone:
            milestone = prj.getMilestone(name=parsed_args.milestone)
        else:
            milestone = None

        if parsed_args.open_only:
            search_states = [
                'Incomplete', 'Confirmed', 'Triaged', 'In Progress',
                'Incomplete (with response)', 'Incomplete (without response)',
            ]
        else:
            search_states = [
                'New', 'Incomplete', 'Confirmed', 'Triaged', 'In Progress',
                'Incomplete (with response)', 'Incomplete (without response)',
                'Opinion', 'Invalid', 'Won\'t Fix', 'Expired',
                'Fix Committed', 'Fix Released',
            ]
        text_fields = [
            'title', 'heat', 'message_count', 'tags', 'private',
            'security_related', 'users_affected_count',
            'number_of_duplicates', 'users_unaffected_count',
            'users_affected_count_with_dupes']
        person_fields = ['owner']
        date_fields = ['date_created', 'date_last_updated']
        collection_size_fields = [
            'activity_collection', 'attachments_collection',
            'bug_tasks_collection', 'bug_watches_collection',
            'cves_collection']

        bt_text_fields = ['importance', 'status', 'is_complete']
        bt_person_fields = ['assignee']
        bt_date_fields = [
            'date_assigned', 'date_closed', 'date_confirmed',
            'date_created', 'date_fix_committed', 'date_fix_released',
            'date_in_progress', 'date_incomplete', 'date_left_closed',
            'date_left_new', 'date_triaged']

        df = pd.DataFrame(columns=(
            text_fields + person_fields + date_fields +
            map(lambda x: x + '_size', collection_size_fields)))
        ms_df = {}

        def collect_bug(bug):
            id = bug.id
            if not (id in df.index):
                df.loc[id] = float('nan')
            for f in text_fields:
                df.loc[id][f] = getattr(bug, f)
            for f in date_fields:
                df.loc[id][f] = getattr(bug, f)
            for f in person_fields:
                if getattr(bug, f) is None:
                    df.loc[id][f] = None
                else:
                    df.loc[id][f] = getattr(bug, f).name
            for f in collection_size_fields:
                df.loc[id][f + '_size'] = len(getattr(bug, f))
            for bt in bug.bug_tasks:
                prj_name = 'unknown_project'
                if bt.target.resource_type_link.endswith('#project_series'):
                    prj_name = bt.target.project.name
                if bt.target.resource_type_link.endswith('#project'):
                    prj_name = bt.target.name
                if bt.milestone is None:
                    ms_name = 'no_milestone'
                else:
                    ms_name = bt.milestone.name
                col_prefix = '%s_%s_' % (prj_name, ms_name)
                try:
                    dfx = ms_df[col_prefix]
                except KeyError:
                    dfx = pd.DataFrame(columns=map(
                        lambda x: col_prefix + x,
                        bt_text_fields + bt_person_fields + bt_date_fields))
                    ms_df[col_prefix] = dfx
                dfx.loc[id] = float('nan')
                for f in bt_text_fields:
                    dfx.loc[id][col_prefix + f] = getattr(bt, f)
                for f in bt_person_fields:
                    if getattr(bt, f) is None:
                        dfx.loc[id][col_prefix + f] = None
                    else:
                        dfx.loc[id][col_prefix + f] = getattr(bt, f).name
                for f in bt_date_fields:
                    df.loc[id][col_prefix + f] = getattr(bt, f)

        collection = prj.searchTasks(
            status=search_states,
            milestone=milestone,
            modified_since=parsed_args.updated_since)
        s = len(collection)
        self.log.info("Found %d bugs" % s)
        i = 0
        for bt in collection:
            i += 1
            self.log.debug("%s: %d/%d %s" % (prj.name, i, s, bt.bug.id))
            collect_bug(bt.bug)

        df = pd.concat([df] + ms_df.values(), axis=1)
        self.log.debug("Saving data to %s" % parsed_args.outfile)
        df.to_csv(parsed_args.outfile, encoding='utf-8')
