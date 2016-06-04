from lpgrabber.boards.dumbboard import DumbBoardCard


def convert_task_to_card(task):
    status = get_task_list_name(task)
    return DumbBoardCard(
        id=task.id, title=task.title, status=status,
        assignee=task.assignee, tags=get_card_tags(task),
        description=get_card_description(task, status)
    )


def get_task_list_name(task):
    list_name = 'Bad Status'
    if task.status in ['Confirmed']:
        if task.assignee is None or task.assignee.is_team:
            list_name = 'Inbox/Need triage'
        else:
            list_name = 'Assigned/Investigating'
    if task.status in ['Incomplete']:
        list_name = 'Incomplete/Need more info'
    if task.status in ['Triaged']:
        list_name = 'Triaged/Ready to be fixed'
    if task.status in ['In Progress']:
        if task.list_reviews():
            list_name = 'In Progress/Need review'
        else:
            list_name = 'In Progress/Working on fix'
    if task.status in ['Fix Committed', 'Fix Released']:
        list_name = 'Fix Committed/Done'
    if task.status in ['Invalid', 'Opinion', 'Won\'t Fix']:
        list_name = 'Won\'t Fix/Done'
    if task.status in ['New']:
        list_name = 'New/Need confirmation'
    if 'blocked' in task.bug.tags:
        list_name = 'Blocked/On hold'
    return list_name


def get_card_tags(task):
    bug = task.bug
    tags = list()
    # TODO(dpyzhov): add tags options
    # # tags = list(set(bug.tags).intersection(self.tag_labels))
    # Each bug should have either team tag or no-team tag or tech-debt tag
    team_tags = filter(lambda x: x.startswith('team-'), bug.tags)
    if team_tags:
        tags += team_tags
    else:
        if 'tech-debt' not in bug.tags:
            tags += ['no-team']
    if not filter(lambda x: x.startswith('area-'), task.bug.tags):
        tags += ['no-area']
    return tags


def get_card_description(task, card_list_name):
    bug = task.bug
    desc = "Created by {0}\n".format(bug.owner_link.split('~')[-1])
    desc += bug.web_link + "\n"
    if card_list_name == 'In Progress/Need review':
        desc += "Reviews:\n" + "\n".join(map(
            lambda x: u"{0} {1}".format(x['url'], ':'.join(x['status'])),
            task.list_reviews()
        )) + "\n"
    desc += "\n----------\n" + bug.description
    return desc[:1000]
