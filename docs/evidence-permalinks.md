# Evidence Permalinks & Unpushed Commits

## Issue
GitHub permalinks in the evidence index were returning 404 errors because they referenced local commits that hadn't been pushed to the remote repository.

## Root Cause
The evidence builder indexes **all local commits** (including unpushed ones) to capture your most recent work. However, GitHub permalinks only work for commits that exist on the remote.

## Solution
M3a now detects and warns about unpushed commits:

```bash
$ roleskills evidence-build --github-user jaybea --chunk-budget 100

Building evidence index for @jaybea...
{
  "chunks_written": 35,
  "repos": 1,
  "commits_selected": 5,
  "commits_pickaxe": 0,
  "commits_stratified": 5,
  "commits_recent": 5,
  "commits_unpushed": 4
}

⚠️  Warning: 4 of 5 commits are not pushed to remote.
   GitHub permalinks will return 404 until you push these commits.
   Run 'git push' to make the evidence links accessible.
```

## How to Fix 404 Links

### Option 1: Push Your Commits (Recommended)
```bash
git push origin feat/m2-llm-jd-parser  # Or your current branch
```

Once pushed, all permalinks will work immediately. No need to rebuild the index.

### Option 2: Only Index Remote Commits
If you only want evidence from pushed commits, filter by remote branches first:
```bash
git log --remotes --oneline  # See what's on remote
# Then only index those commits manually
```

## Why Index Unpushed Commits?

Indexing local commits is beneficial because:
1. **Captures WIP** - Your current work is often your most relevant evidence
2. **Iterative building** - Build your dossier as you work, before pushing
3. **Stable permalinks** - Links become valid once you push (no rebuild needed)
4. **Branch work** - Feature branches are indexed even before PR

## Technical Details

### Permalink Format
```
https://github.com/{owner}/{repo}/blob/{commit_sha}/{path}#L{start}-L{end}
```

Example:
```
https://github.com/ammons-datalabs/RoleSkills/blob/37ef081aa417664f8fb2035796e7088312df9d84/src/roleskills/cli.py#L1-L40
```

### Checking Commit Status
```bash
# Check if a commit is on remote
git branch -r --contains <commit_sha>

# See unpushed commits
git log origin/main..HEAD

# See what's on remote
git log --remotes
```

## Stats Field
The `commits_unpushed` field in stats tells you how many selected commits are local-only:

```json
{
  "commits_selected": 5,
  "commits_unpushed": 4
}
```

This means 4 out of 5 commits are not yet on any remote branch.
