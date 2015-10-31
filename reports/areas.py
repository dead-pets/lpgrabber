#!/usr/bin/env python
#from __future__ import unicode_literals

import pandas as pd
from io import open

bugs_fuel_csv_filename = '/users/dima/Downloads/bugs-fuel-lpgrabber-all-9-2015-10-30.csv'
bugs_fuel_delta_csv_filename = '/users/dima/Downloads/bugs-fuel-lpgrabber-delta-56-2015-10-30.csv'
teams_csv_filename = '/users/dima/Downloads/teams-lpgrabber-delta-56-2015-10-30.csv'
report_filename = 'report.html'
cur_ms = '8.0'
cur_prj = 'fuel'
approved_areas = [
    'area-python', 'area-library', 'area-ui', 'area-build', 'area-ci',
    'area-devops', 'area-qa', 'area-docs', 'area-mos', 'area-linux',
    'area-partners', 'area-plugins']
show_columns = ['area', 'web_link', 'bug_type', 'severity', 'title', 'tags', 'team', 'assignee', 'status']

pd.set_option('display.width', 1000)
df = pd.read_csv(bugs_fuel_csv_filename, low_memory=False, index_col=0, encoding='utf-8')
df_teams = pd.read_csv(teams_csv_filename, low_memory=False, index_col=0, encoding='utf-8')

if bugs_fuel_delta_csv_filename:
    df_delta = pd.DataFrame.from_csv(bugs_fuel_delta_csv_filename)
    cols_to_use = df_delta.columns.difference(df.columns)
    df = pd.merge(df, df_delta[cols_to_use], left_index=True, right_index=True, how='outer')
    df.update(df_delta.drop_duplicates(keep='last'))

dftt = pd.Series(df_teams.apply(lambda k: ' '.join([i for i in k if not isinstance(i, float)]), axis=1), name='team')

for t in df_teams.columns:
    dftt.loc[t] = t

df['web_link'] = ["https://launchpad.net/bugs/%s" % x for x in df.index]
df['tags'] = [x[1:-1].split(', ') for x in df.tags]
df['assignee'] = df[cur_prj + '_' + cur_ms + '_assignee']
df['importance'] = df[cur_prj + '_' + cur_ms + '_importance']
df['status'] = df[cur_prj + '_' + cur_ms + '_status']

# Add teams list to each bug
df = df.join(dftt, on='assignee')

# Remove all bugs except targeted to current milestone
df = df[df.status.notnull()]


def get_bug_type(tags):
    if 'feature' in tags:
        return 'feature'
    if 'covered-by-bp' in tags:
        return 'bp'
    if 'need-bp' in tags:
        return 'bp'
    if 'customer-found' in tags:
        return 'top bug'
    if 'support' in tags:
        return 'top bug'
#    if 'long-haul-testing' in tags:
#        return 'top bug'
#    if 'swarm-blocker' in tags:
#        return 'top bug'
    if 'tech-debt' in tags:
        return 'tech debt'
    return 'bug'


def get_bug_severity(l):
    if l in ['Critical', 'High']:
        return 'high'
    if l in ['Medium', 'Low', 'Wishlist']:
        return 'low'
    return 'untriaged'


def get_bug_short_status(s):
    if s in ['New', 'Confirmed', 'Triaged', 'In Progress']:
        return 'open'
    if s in ['Incomplete', 'Incomplete (with response)', 'Incomplete (without response)']:
        return 'incomplete'
    if s in ['Opinion', 'Invalid', "Won't Fix", 'Expired']:
        return 'rejected'
    if s in ['Fix Committed', 'Fix Released']:
        return 'fixed'
    return 'unknown'


def get_bug_close_date(bug):
    field_prefix = cur_prj + '_' + cur_ms
    status = bug[field_prefix + '_status']
    if status == 'Fix Committed':
        return bug[field_prefix + '_date_fix_committed']
    if status == 'Fix Released':
        if bug[field_prefix + '_date_fix_committed']:
            return bug[field_prefix + '_date_fix_committed']
        return bug[field_prefix + '_date_fix_released']
    if status == 'Incomplete':
        return bug[field_prefix + '_date_incomplete']
    if status in ['Opinion', 'Invalid', "Won't Fix", 'Expired']:
        return bug[field_prefix + '_date_closed']
    return float('nan')


def get_bug_area(bug):
    if filter(lambda x: x.startswith('area-'), bug.tags):
        if type(bug.assignee) == str and bug.assignee.startswith('fuel-'):
            area_suffix = filter(lambda x: x.startswith('area-'), bug.tags)[0][5:]
            assignee_suffix = bug.assignee[5:]
            if area_suffix == 'python' and assignee_suffix == 'octane':
                return 'area-python'
            if area_suffix == 'partners' and assignee_suffix.startswith('partner'):
                return 'area-partners'
            if area_suffix == 'plugins' and assignee_suffix.startswith('plugin'):
                return 'area-plugins'
            if area_suffix != assignee_suffix:
                return 'changed-team'
        return ' '.join(filter(lambda x: x.startswith('area-'), bug.tags))
    if type(bug.assignee) == float:
        return 'noassignee'
    if type(bug.team) == float:
        return 'noteam'
    if bug.team=='fuel-python':
        return 'python'
    if bug.team in ['fuel-library', 'fuel-library fuel-security']:
        return 'library'
    if bug.team=='fuel-ui':
        return 'ui'
    if bug.team in ['fuel-qa', 'mos-qa']:
        return 'qa'
    if bug.team=='fuel-devops':
        return 'devops'
    if bug.team=='fuel-ci':
        return 'ci'
    if bug.team=='fuel-docs':
        return 'docs'
    if bug.team=='fuel-build':
        return 'build'
    if bug.team in ['fuel-partner-engineering', 'fuel-partner-core']:
        return 'partners'
    if bug.team in ['mos-linux']:
        return 'linux'
    if bug.team in ['mos-puppet', 'mos-ceph', 'mos-ironic', 'mos-nova', 'mos-oslo', 'mos-packaging']:
        return 'mos'
    if bug.team in ['mos-sahara', 'mos-cinder', 'mos-ceilometer', 'mos-da mos-ironic mos-puppet',
        'mos-oslo mos-security', 'mos-keystone', 'mos-lma-toolchain', 'mos-da mos-puppet mos-ceilometer',
        'mos-neutron']:
        return 'mos'
    if bug.team in ['fuel-plugins-bugs', 'fuel-plugin-zabbix', 'fuel-plugin-contrail']:
        return 'plugins'
    if 'fuel-ci' in bug.tags:
        return 'ci'
    if 'devops' in bug.tags:
        return 'devops'
    if 'fuel-build' in bug.tags:
        return 'build'
    if 'system-tests' in bug.tags:
        return 'qa'
    if 'docs' in bug.tags:
        return 'docs'
    if 'module-octane' in bug.tags:
        return 'octane'
    if 'module-build' in bug.tags:
        return 'build'
    if 'ubuntu-bootstrap' in bug.tags:
        return 'ubuntu-bootstrap'
    if 'mos-linux' in bug.tags:
        return 'mos'
    if 'murano' in bug.tags:
        return 'mos'
    if 'iso' in bug.tags:
        return 'build'
    if 'partner' in bug.tags:
        return 'partners'
    if 'cinder' in bug.tags:
        return 'mos'
    if bug.assignee in ['sbogatkin', 'vkuklin', 'zynzel', 'pzhurba', 'sovsianikov', 'nkoshikov']:
        return 'library'
    if bug.assignee in ['skolekonov']:
        return 'mos'
    if bug.assignee in ['prmtl', 'mpolenchuk', 'dstepanenko', 'sslypushenko', 'dbogun']:
        return 'python'
    if bug.assignee in ['aarzhanov']:
        return 'partners'
    if bug.assignee in ['amogylchenko', 'isuzdal']:
        return 'linux'
    if bug.assignee in ['dtrishkin', 'mivanov', 'degorenko']:
        return 'mos'
    if bug.assignee in ['afedorova']:
        return 'ci'
    if bug.assignee in ['tnurlygayanov', 'aurlapova', 'apanchenko-8']:
        return 'qa'
    if bug.assignee in ['teran']:
        return 'devops'
    return 'unknown'


df['bug_type'] = [get_bug_type(x) for x in df.tags]
df['severity'] = [get_bug_severity(x) for x in df['importance']]
df['short_status'] = [get_bug_short_status(x) for x in df['status']]
df['area'] = df.apply(get_bug_area, axis=1)
df['date_closed'] = df.apply(get_bug_close_date, axis=1)
week_start = '2015-10-26'

r = open(report_filename, 'w')
r.write(u"<h1>Bugs by area</h1>")
r.write(unicode(df['area'].value_counts()))
r.write(u"<h1>Open bugs by area</h1>")
r.write(unicode(df[df.short_status=='open']['area'].value_counts()))
r.write(u"<h1>Bugs on wrong team</h1>")
r.write(df[df.area=='changed-team'][show_columns].to_html())
r.write(u"<h1>Bugs on unknown teams</h1>")
r.write(df[~df.area.isin(approved_areas + ['changed-team'])][show_columns].to_html())


for area in approved_areas:
    r.write(u"<h1>%s</h1>" % area)
    r.write(u"<h2>Top bugs created this week</h2>")
    r.write(df.query("area == @area & date_created >= @week_start & (bug_type == 'top bug' | severity in ['high', 'untriaged'])")[show_columns].to_html())
    r.write(u"<h2>Older top bugs closed this week</h2>")
    r.write(df.query("area == @area & date_created < @week_start & date_closed >= @week_start & (bug_type == 'top bug' | severity in ['high', 'untriaged'])")[show_columns].to_html())
    r.write(u"<h2>Older open top bugs</h2>")
    r.write(df.query("area == @area & date_created < @week_start & short_status == 'open' & (bug_type == 'top bug' | severity in ['high', 'untriaged'])")[show_columns].to_html())
    r.write(u"<h2>Medium bugs created this week</h2>")
    r.write(df.query("area == @area & date_created >= @week_start & bug_type != 'top bug' & severity == 'low'")[show_columns].to_html())
    r.write(u"<h2>Older medium bugs closed this week</h2>")
    r.write(df.query("area == @area & date_created < @week_start & date_closed >= @week_start & bug_type != 'top bug' & severity == 'low'")[show_columns].to_html())
    r.write(u"<h2>Older open medium bugs</h2>")
    r.write(df.query("area == @area & date_created < @week_start & short_status == 'open' & bug_type != 'top bug' & severity == 'low'")[show_columns].to_html())
