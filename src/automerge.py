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
parser.add_argument('--comment', action='store_true', default=False, help='Set Commit Message to Title and URL. Default to using existing PR Title / Body')
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
repo = github.get_repo(repo)

# 1. Get PRs that are:
# - Open.
open_prs = []
for pr in repo.get_pulls():
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
_LOGGER.info(f'Approved PRs:\n{pr_string}\n')
if not automerge_prs:
    _LOGGER.info(' Quitting.')
    sys.exit(0)
    
# 3. Sort PRs into 3 categories 
# - Up-to-date and passing
# - Up-to-date and behind 
# - Pending/Blocked PRs
up_to_date_passing_prs = []
do_nothing_pending_prs = []
out_of_date_passing_prs = []
for pr in automerge_prs:
    base_branch = repo.get_branch(pr.base.ref)
    if base_branch.protected:
        required_status_checks = base_branch.get_required_status_checks()
        latest_commit = pr.get_commits().reversed[0]
        latest_commit_checks = {check_run.name: check_run for check_run in latest_commit.get_check_runs()}
        all_checks_passed = True
        for required_check in required_status_checks.contexts:
            if required_check not in latest_commit_checks:
                print(f"Required check {required_check} is missing in the latest commit.")
                all_checks_passed = False
            else:
                check_run = latest_commit_checks[required_check]
                if check_run.conclusion == 'success':
                    print(f"Required check {required_check} passed on PR#{pr.number}")
                else:
                    print(f"Required check {required_check} failed or is pending on PR#{pr.number}")
                    all_checks_passed = False
    commit = [c for c in pr.get_commits() if c.sha == pr.head.sha][0]
    combined_status = commit.get_combined_status().state
    if pr.mergeable_state == 'clean' and all_checks_passed:
        up_to_date_passing_prs.append(pr)
    elif pr.mergeable_state == 'behind' or pr.mergeable_state == 'blocked':
        if all_checks_passed:
            out_of_date_passing_prs.append(pr)
        else:
            do_nothing_pending_prs.append(pr)
pr_string = '\n'.join(map(pr_to_display_string, up_to_date_passing_prs))
_LOGGER.info(f' Automerge Approved Up-to-Date PRs:\n{pr_string}\n')
pr_string = '\n'.join(map(pr_to_display_string, out_of_date_passing_prs))
_LOGGER.info(f' Update Out-of-Date Passing PRs:\n{pr_string}\n')
pr_string = '\n'.join(map(pr_to_display_string, do_nothing_pending_prs))
_LOGGER.info(f' Do Nothing Pending/Failing PRs:\n{pr_string}\n')

while up_to_date_passing_prs:
    pr = up_to_date_passing_prs[0]
    if args.dry_run:
        _LOGGER.info(f'Would have merged PR:\n{pr_to_display_string(pr)}\n')
        _LOGGER.info(f'With Comment: {args.comment}')
        _LOGGER.info(f"With Comment Message would be: \nAutomerged: [{pr.title}]({pr.html_url})")
    else:
        if args.comment:
            pr.merge(merge_method='squash', commit_message=f'Automerged {pr.html_url}: {pr.title}')
        else:
            pr.merge(merge_method='squash')
    up_to_date_passing_prs.pop(0)

while out_of_date_passing_prs:
    pr = out_of_date_passing_prs[0]
    if args.dry_run:
        _LOGGER.info(f'Would have updated PR:\n{pr_to_display_string(pr)}\n')
    else:
        pr.update_branch()
    out_of_date_passing_prs.pop(0)

_LOGGER.info('Done.')
