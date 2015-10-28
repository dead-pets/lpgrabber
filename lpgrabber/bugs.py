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
        parser.add_argument(
            '--add-collections', action='store_true',
            help='Grab extra collections numbers')
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

        def get_user_id_by_link(link):
            # Guess id from link in order to avoid extra network request
            # Link looks like https://api.launchpad.net/devel/~dpyzhov
            if link is None:
                return None
            return link[link.find('~')+1:]

        def get_project_name_by_link(link):
            # Guess project from project or series link for speedup
            return link.split('/')[4]

        def get_milestone_name_by_link(link):
            # Save some time. Link looks like this:
            # https://api.launchpad.net/devel/fuel/+milestone/8.0
            if link is None:
                return None
            return link.split('/')[6]

        def collect_bug(bug_task):
            bug = bug_task.bug
            s = pd.Series(name=bug.id)
            for f in text_fields:
                s[f] = getattr(bug, f)
            for f in date_fields:
                s[f] = str(getattr(bug, f))
            for f in person_fields:
                s[f] = get_user_id_by_link(getattr(bug, f + '_link'))
            if parsed_args.add_collections:
                for f in collection_size_fields:
                    s[f + '_size'] = len(getattr(bug, f))
            for bt in bug.bug_tasks:
                prj_name = get_project_name_by_link(bt.target_link)
                ms_name = get_milestone_name_by_link(bt.milestone_link)
                col_prefix = '%s_%s_' % (prj_name, ms_name)
                for f in bt_text_fields:
                    s[col_prefix + f] = getattr(bt, f)
                for f in bt_person_fields:
                    s[col_prefix + f] = get_user_id_by_link(getattr(bt, f + '_link'))
                for f in bt_date_fields:
                    s[col_prefix + f] = str(getattr(bt, f))
            return s

        df = pd.DataFrame()
        collection = prj.searchTasks(
            status=search_states,
            milestone=milestone,
            modified_since=parsed_args.updated_since)
        s = len(collection)
        self.log.info("Found %d bugs" % s)
        i = 0
        for bt in collection:
            i += 1
            series = collect_bug(bt)
            self.log.debug("%s: %d/%d %s" % (prj.name, i, s, series.title))
            df = df.append(series)
            self.log.debug("Report size is %d lines" % len(df))

        if milestone:
            lp_series = milestone.series_target
            # For some reason I can't get access to methods if I don't access
            # some property before. Magic stuff
            lp_series.name
            collection = lp_series.searchTasks(
                status=search_states,
                milestone=milestone,
                modified_since=parsed_args.updated_since)
            s = len(collection)
            self.log.info("Found %d bugs on %s series" % (s, lp_series.name))
            i = 0
            for bt in collection:
                i += 1
                series = collect_bug(bt)
                self.log.debug("%s: %d/%d %s" % (prj.name, i, s, series.title))
                df = df.append(series)
                self.log.debug("Report size is %d lines" % len(df))

        self.log.debug("Saving data to %s" % parsed_args.outfile)
        df.to_csv(parsed_args.outfile, encoding='utf-8')
