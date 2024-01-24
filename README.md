Example workflow using Automerge across an Github Organization
==============================================================
This example workflow will run every 20 minutes and will automerge any PRs that are ready to be merged.  It will also cancel any previous runs of the workflow if they are still running.

From the repository the workflow is running from it will require a JSON file called `automerge.json` that contains a list of repositories to run the workflow on.  The JSON file should be in the following format:

```json
[
  "repo1",
  "repo2",
  "repo3"
]
```
In .github/workflows/automerge.yml
```yaml
name: Test Workflow

on: [push, pull_request, workflow_dispatch]

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
      - name: 'Check Automerge Repo to Test'
        uses: actions/checkout@v4.0.0

      - name: 'Automerge runtimeverification/${{ matrix.value }}'
        uses: ./ # This uses the action in the root directory
        with:
          org: 'runtimeverification'
          repo: ${{ matrix.value }}
          token: ${{ secrets.GITHUB_PAT }}

```