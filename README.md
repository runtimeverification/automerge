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
name: 'Automerger'
on:
  workflow_dispatch:
  schedule:
    - cron: '*/20 * * * *'
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:

  list:
    name: 'List Repos'
    runs-on: [linux]
    outputs:
      matrix: ${{ steps.list.outputs.value }}
    steps:
      - name: 'Check out devops repo'
        uses: actions/checkout@v3
      - id: list
        name: 'List automerge repos'
        run: echo "value=$(cat automerge.json | tr -d '\n')" >> $GITHUB_OUTPUT

  automerge:
    name: 'Automerge'
    runs-on: [self-hosted, linux, flyweight]
    needs: list
    strategy:
      fail-fast: false
      matrix:
        value: ${{fromJson(needs.list.outputs.matrix)}}
    steps:
      - name: 'Check out devops repo'
        uses: actions/checkout@v3
      - name: 'Automerge runtimeverification/${{ matrix.value }}'
        uses: ./.github/actions/automerge
        with:
          repo: ${{ matrix.value }}
          token: ${{ secrets.JENKINS_GITHUB_PAT }}
```