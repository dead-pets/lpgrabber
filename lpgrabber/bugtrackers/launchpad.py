from launchpadlib.launchpad import Launchpad
from pygerrit.rest import GerritRestAPI
import re


class LaunchpadTracker(object):
    def __init__(self):
        self.lp = Launchpad.login_with(
            'lp-report-bot', 'production', version='devel')

    def filter(self, filter):
        for prj_name in filter['projects']:
            pass

    @classmethod
    def update_argparse(cls, parser):
        parser.add_argument(
            '--filter', type=str, action='append', required=True,
            help="List of params for searchTasks",
        )
        parser.add_argument(
            '--project', type=str, action='append', required=True,
            help="Project"
        )
        return parser


class LaunchpadTrackerTask(object):
    # TODO(dpyzhov): move gerrit iterations to the separate module
    def list_reviews(self):
        bug = self.bug
        gerrits = [
            'https://review.openstack.org/', 'https://review.fuel-infra.org/']
        reviews = []
        # Message number 0 is description
        is_description = True
        for msg in bug.messages:
            if is_description:
                is_description = False
                continue
            for g in gerrits:
                reviews += re.findall(g + '\d+', msg.content)
                long_reviews = re.findall(g + '#/c/\d+', msg.content)
                for u in long_reviews:
                    reviews += [u.replace('#/c/', '')]
        open_reviews = []
        for rev_url in set(reviews):
            [base_url, id] = rev_url.rsplit('/', 1)
            rest = GerritRestAPI(base_url)
            try:
                review = rest.get('/changes/{0}/detail'.format(id))
                if review['status'] == 'NEW':
                    status = []
                    if 'rejected' in review['labels']['Workflow']:
                        status.append('WIP')
                    if 'disliked' in review['labels']['Verified']:
                        status.append('FAIL')
                    open_reviews.append({'url': rev_url, 'status': status})
            except Exception:
                pass
        return open_reviews
