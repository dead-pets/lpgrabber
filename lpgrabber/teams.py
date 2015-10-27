import logging

import argparse
from cliff.command import Command
from launchpadlib.launchpad import Launchpad
import pandas as pd


class Teams(Command):
    "Download team members."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Teams, self).get_parser(prog_name)
        parser.add_argument(
            'substring', type=str, nargs='+', help='part of name')
        parser.add_argument(
            '--outfile', type=argparse.FileType('w'), default='teams.csv',
            help='Report destination')
        return parser

    def take_action(self, parsed_args):
        self.log.debug('connecting to Launchpad')
        lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')

        teams_map = {}
        for team_filter in parsed_args.substring:
            for team in lp.people.findTeam(text=team_filter):
                self.log.debug("found team: %s" % team.name)
                teams_map[team.name] = []
        self.log.debug("Getting teams members")
        i = 0
        for t in teams_map:
            i += 1
            self.log.debug("%d/%d %s" % (i, len(teams_map), t))
            for p in lp.people[t].members:
                try:
                    teams_map[t] += [p.name]
                except KeyError:
                    teams_map[t] = [p.name]

        df_teams = pd.DataFrame(columns=teams_map.keys())

        for t in teams_map.keys():
            for p in teams_map[t]:
                try:
                    df_teams.loc[p][t] = t
                except KeyError:
                    df_teams.loc[p] = float('nan')
                    df_teams.loc[p][t] = t

        self.log.debug("Saving data to %s" % parsed_args.outfile)
        df_teams.to_csv(parsed_args.outfile, encoding='utf-8')
