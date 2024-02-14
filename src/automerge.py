#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
import argparse

from github import Github
from typing import Final

# Collect command arguments from argparse
parser = argparse.ArgumentParser(description='Automerge approved PRs.')
parser.add_argument('--repo', type=str, help='The repository to check.')
parser.add_argument('--org', type=str, help='The GitHub organization to check.')
parser.add_argument('--dry-run', action='store_true', default=False, help='Enable Debug/Dry-Run mode.')
args = parser.parse_args()

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'
logging.basicConfig(level=logging.INFO)


def pr_to_display_string(pr):
    return f'- {pr.number}: {pr.title}\n\t\t{pr.html_url}'


def run_git_command(command_args: str) -> subprocess.CompletedProcess:
    command = ['git'] + command_args.split(' ')
    _LOGGER.debug(f'Running: {" ".join(command)}')
    if args.dry_run:
        _LOGGER.info(f'Would have run: {" ".join(command)}')
        return subprocess.CompletedProcess(args=command, returncode=0)
    try:
        res = subprocess.run(command, stdout=None, stderr=None, check=False, text=True)
    except subprocess.CalledProcessError as err:
        _LOGGER.error(f'Completed with status {err.returncode}: {" ".join(command)}')
        raise
    return res


github = Github(login_or_token=os.environ['GITHUB_TOKEN'])
repo = args.org + "/" + args.repo

# 1. Get PRs that are:
# - Open.
open_prs = []
for pr in github.get_repo(repo).get_pulls():
    if pr.state == 'open':
        open_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, open_prs))
_LOGGER.info(f' PRs:\n{pr_string}\n')
if not open_prs:
    _LOGGER.info(' Quitting.')

# 2. Get PRs that are:
    # - Open,
    # - Labeled as `automerge`, and
    # - Approved.
automerge_prs = []
for pr in open_prs:
    labels = [label.name for label in pr.get_labels()]
    reviews = sorted([(r.state, r.submitted_at) for r in pr.get_reviews()], key=lambda x: x[1], reverse=True)
    reviews = [state for state, _ in reviews]
    if 'automerge' in labels:
        approved = False
        for i in reviews:
            if i == 'APPROVED':
                approved = True
                break
            if i != 'COMMENTED':
                break
        if approved:
            automerge_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, automerge_prs))
_LOGGER.info(f' Automerge approved PRs:\n{pr_string}\n')
if not automerge_prs:
    _LOGGER.info(' Quitting.')
    sys.exit(0)

# 3. Get PRs that are:
# - Open,
# - Labelled as `automerge`,
# - Approved,
# - Up-to-date, and
# - Passing tests.
automerge_up_to_date_prs = []
for pr in automerge_prs:
    is_up_to_date = run_git_command(f'merge-base --is-ancestor {pr.base.sha} {pr.head.sha}').returncode == 0
    if pr.mergeable_state == 'clean' and is_up_to_date:
        automerge_up_to_date_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, automerge_up_to_date_prs))
_LOGGER.info(f' Automerge approved up-to-date PRs:\n{pr_string}\n')

# 4. Get PRs that are:
# - Open,
# - Labelled as `automerge`,
# - Approved, and
# - Up-to-date.
# If so, merge
while automerge_up_to_date_prs:
    pr = automerge_up_to_date_prs[0]
    _LOGGER.info(f' Merging PR:\n{pr_to_display_string(pr)}\n')
    if args.dry_run:
        _LOGGER.info(f'Would have merged PR:\n{pr_to_display_string(pr)}\n')
    else:
        pr.merge(merge_method='squash', merge_title=f'Auto Mergerge: {pr.number}', merge_message='Title: {pr.title}\nURL: {pr.html_url}\n')
    automerge_up_to_date_prs.pop(0)

# 5. Get PRs that are:
    # - Open,
    # - Labelled as `automerge`,
    # - Approved,
    # - Up-to-date, and
    # - Pending tests.
automerge_up_to_date_pending_prs = []
for pr in automerge_prs:
    is_up_to_date = run_git_command(f'merge-base --is-ancestor {pr.base.sha} {pr.head.sha}').returncode == 0
    commit = [c for c in pr.get_commits() if c.sha == pr.head.sha][0]
    is_failing = commit.get_combined_status().state == 'failure'
    if pr.mergeable_state == 'blocked' and is_up_to_date and not is_failing:
        print(commit.get_combined_status())
        automerge_up_to_date_pending_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, automerge_up_to_date_pending_prs))
_LOGGER.info(f' Waiting on approved up-to-date pending/failing PRs:\n{pr_string}\n')


# 6. Get PRs that are:
# - Open,
# - Labelled as `automerge`,
# - Approved,
# - Out-of-date, and
# - Passing tests.
# If so, update the branch.
automerge_out_of_date_passing_prs = []
for pr in automerge_prs:
    if pr.mergeable_state == 'behind':
        automerge_out_of_date_passing_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, automerge_out_of_date_passing_prs))
_LOGGER.info(f' Approved out-of-date passing PRs:\n{pr_string}\n')
if automerge_out_of_date_passing_prs:
    pr = automerge_out_of_date_passing_prs[0]
    _LOGGER.info(f' Updating PR:\n{pr_to_display_string(pr)}\n')
    pr.update_branch()
