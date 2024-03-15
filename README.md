# About Automerge Action 
This action is intended to be used in tandem with a CI workflow. 
This workflow requires a github token  with read/write access to all the repositories it will be tracking 

Any PRs that meet the following criteria will be automerged:
- PR is open
- PR is mergeable
- PR is passing test
- PR is approved by at least one reviewer
- PR is up-to-date with the base branch

Any PR with the following criteria will be updated and test will be run before merging:
- PR is open
- PR is approved
- PR is passing PR Tests
- PR is out-of-date

## Table of Contents
- [Automerge PR Action](#automerge-pr-action)
  - [Table of Contents](#table-of-contents)
  - [Inputs](#inputs)
  - [Outputs](#outputs)
  - [Example workflow using Automerge across a Github Organization](#example-workflow-using-automerge-across-a-github-organization)
  - [The Workflow](#the-workflow)
  - [Reduce CI Pressure](#reduce-ci-pressure)
  - [Run Locally](#run-locally)

# Example workflow using Automerge across a Github Organization
This example workflow will run every 20 minutes and will automerge PRs for tracked repositories in the organization.

This workflow is recommended for setup in a CI/CD Devops dedicated repostiory. 

For the example a JSON file called `automerge.json` contains a list of repositories to track PR status for merging/updates.
The JSON file should be in the following format:
```json
[
  "repo1",
  "repo2",
  "repo3"
]
```

## The Workflow

In a workflow we will call `.github/workflows/automerge.yml`. 
The workflow will run as many jobs in parallel as possible.
```yaml
name: Example Automerge Workflow
on:
  workflow_dispatch:
  schedule:
    - cron: '*/20 * * * *'
jobs:
  list:
    name: 'List Repos'
    runs-on: [ubuntu-latest]
    outputs:
      matrix: ${{ steps.list.outputs.value }}
    steps:
      - name: 'Check out devops repo'
        uses: actions/checkout@v4.0.0
      - id: list
        name: 'List automerge repos'
        run: echo "value=$(cat test/automerge.json | tr -d '\n')" >> $GITHUB_OUTPUT
  
  automerge-test:
    name: 'Automerge'
    runs-on: [ubuntu-latest]
    needs: list
    strategy:
      fail-fast: false
      matrix:
        value: ${{fromJson(needs.list.outputs.matrix)}}
    steps:
      - name: 'Automerge runtimeverification/${{ matrix.value }}'
        uses: ./ # This uses the action in the root directory
        with:
          org: 'runtimeverification' # As long as the token you use has access, any org is valid here
          repo: ${{ matrix.value }}
          token: ${{ secrets.GITHUB_PAT }}
```

## Reduce CI Pressure

If less CI Pressure is desired, the workflow can be modified to run on sequentially
```yaml
name: Test Workflow
on:
  workflow_dispatch:
  schedule:
    - cron: '*/20 * * * *'
...
...
...
  automerge-test:
    name: 'Automerge'
    runs-on: [ubuntu-latest]
    needs: list
    strategy:
      fail-fast: false
      max-parallel: 1 # Or any integer up to 256 set by github actions run limit. 
      matrix:
        value: ${{fromJson(needs.list.outputs.matrix)}}
    steps:
...
...
```

# Run Locally
Checkout the repository you wish to run automerge on to a local directory. 
```bash
git clone git@github.com:org/automerge.git
cd automerge
```

Now you need to run the command from this new directory 
```bash
$(pwd)/../src/automerge.py --org runtimeverification --repo automerger-test --dry-run
```

Recommended to first review the actions before running without. Then remove the `--dry-run` flag to run the action. 

# Testing
## [test.yaml](.github/workflows/test.yaml)

 ### Purpose:
 - The purpose of the test is to import automerger action.
 - Evaluate the test Scenarios of a Live Test Setup and Report back the values
 
 ### Usage:
 - The test.yaml file is used by the automerger to determine which pull requests to merge and under what conditions.
 - It specifies the target repository, the specific states of the pull requests to test against, and the actions to perform.


 ### Note:
 - Results MUST BE MANUALLY VERIFIED BEFORE MERGE
 - The test.yaml file should be updated whenever there are changes to the test scenarios or configurations.
 - It is important to ensure that the test.yaml file accurately reflects the desired behavior of the automerger.

 For more information, please refer to the following resources:
 - [Link to the repository rutimeverification/automerger-test](https://github.com/runtimeverification/automerger-test)
 - [Link to the live pull requests in the repository](https://github.com/runtimeverification/automerger-test/pulls)

