# CLAUDE.md

Notes for Claude Code working in this repo. `README.md` is the user-facing doc; keep it in
sync when you change the schedule, triggers, retries, monitoring or CSV columns.

## What this is

- `fetcher.py` scrapes daily LME prices for six metals from westmetall.com and writes
  `data/<metal>.csv`.
- `healthcheck.py` sends best-effort Healthchecks.io pings (start / success / fail).
- `.github/workflows/refresh.yml` runs the fetch daily at 20:00 UTC on `ubuntu-latest` and
  commits the CSVs.

The daily job runs only on GitHub Actions. Nothing is scheduled on any local machine, so a
dev machine is only for editing and testing, and replacing one doesn't affect the job.

## Platform

Development moved from Linux to Windows in November 2026. CI still runs on Linux.

- Claude Code on Windows runs its Bash tool through Git Bash, so commands in this file are
  written for Git Bash. PowerShell versions are under
  [PowerShell equivalents](#powershell-equivalents).
- Use the project virtualenv's interpreter, `.venv/Scripts/python`, for everything. Don't use
  `python3`: on Windows it is usually the Microsoft Store stub. Shell state doesn't carry over
  between commands, so call the venv interpreter directly instead of activating the venv.
  On Linux or macOS the path is `.venv/bin/python`.
- Code must keep working on Linux, because CI runs there. Build paths with `pathlib` (as
  `DATA_DIR` does), never hard-code `\`, and keep the workflow steps in bash.
- Read [Line endings](#line-endings) before committing anything under `data/`.

## Setting up a new Windows machine

One-time steps, in PowerShell. Open a new terminal after the `winget` installs so `PATH`
picks them up.

1. **Install the tools.**

   ```powershell
   winget install --id Git.Git -e              # Git for Windows, includes Git Bash
   winget install --id Python.Python.3.12 -e   # same minor version as CI
   winget install --id GitHub.cli -e
   irm https://claude.ai/install.ps1 | iex     # Claude Code (needs Git for Windows)
   ```

   If Claude Code can't find Git Bash, set the `CLAUDE_CODE_GIT_BASH_PATH` environment
   variable to `C:\Program Files\Git\bin\bash.exe`.

2. **Sign in to GitHub** as `c-harsha`, and let `gh` handle Git credentials over HTTPS:

   ```powershell
   gh auth login --git-protocol https --web
   ```

   To use SSH instead (the old machine did): create a key with `ssh-keygen -t ed25519`, add it
   with `gh ssh-key add $HOME\.ssh\id_ed25519.pub --title "<machine name>"`, and run
   `gh config set git_protocol ssh` before cloning.

3. **Set your Git identity** to the same name and email as the old machine, so commits stay
   linked to the GitHub account (`git config --global --list` on the old machine shows them).
   Then check line-ending handling:

   ```powershell
   git config --global user.name  "<same as old machine>"
   git config --global user.email "<same as old machine>"
   git config --global core.autocrlf    # should print: true (the Git for Windows default)
   ```

   If it prints anything else, run `git config --global core.autocrlf true`.

4. **Clone** into a folder OneDrive doesn't sync. Desktop and Documents often are synced, and
   OneDrive can lock files inside `.git`. For example:

   ```powershell
   mkdir C:\dev -Force; cd C:\dev
   gh repo clone c-harsha/lme
   cd lme
   ```

5. **Create the virtualenv and install the pinned dependencies.** `.venv/` is git-ignored.

   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\python.exe -m pip install --upgrade pip
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

6. **Check that it works** with the commands under [Commands](#commands): compile, the
   no-op ping check, the live parsing check, and `gh run list --limit 3`. Afterwards
   `git status` should be clean.

7. **Start Claude Code** with `claude` from the repo folder. There's nothing to copy over:
   - `.claude/settings.local.json` is git-ignored and per machine. The old one only allowed
     some `python3`, `git` and `gh` commands; approve them again as prompts come up.
   - Claude Code's project memory for this repo on the old machine was empty.

8. **Leave secrets on GitHub.** `HC_PING_URL` exists only as a GitHub Actions secret
   (`gh secret list` shows it). Don't copy it to the new machine or into any file.

### Retiring the old machine

1. In the old checkout, make sure nothing is left behind: `git status` is clean, and
   `git log origin/main..HEAD` and `git stash list` print nothing.
2. Remove its SSH key from GitHub: `gh ssh-key list`, then `gh ssh-key delete <id>` (or
   GitHub → Settings → SSH and GPG keys).
3. Sign out with `gh auth logout`. If Git there uses `credential.helper store`, delete
   `~/.git-credentials` (it holds a token in plain text) and revoke that token on GitHub.

## Commands

Git Bash, from the repo root:

```bash
.venv/Scripts/python -m pip install -r requirements.txt   # CI uses Python 3.12
.venv/Scripts/python -m py_compile fetcher.py healthcheck.py

# Check parsing against live data for every metal, without writing CSVs:
.venv/Scripts/python - <<'EOF'
import datetime, fetcher
year = datetime.date.today().year
for code in fetcher.METALS:
    print(code, len(fetcher._clean(fetcher._fetch_year(code, year))), "rows")
EOF

# Pings must do nothing without HC_PING_URL (prints "no-op OK", sends nothing):
env -u HC_PING_URL .venv/Scripts/python -c "import healthcheck; healthcheck.ping_start(); healthcheck.ping_success('x'); healthcheck.ping_fail('y'); print('no-op OK')"

gh run list --limit 3                      # recent refresh runs
gh run watch <run-id> --exit-status
```

`.venv/Scripts/python fetcher.py` does a full refresh and overwrites `data/*.csv`. If it fails,
it sleeps 2–3 hours before retrying, so don't run it in the foreground while westmetall.com is
failing (Ctrl+C stops it). Don't set `HC_PING_URL` locally: it would ping the production check.

### PowerShell equivalents

```powershell
.venv\Scripts\python.exe -m py_compile fetcher.py healthcheck.py

@'
import datetime, fetcher
year = datetime.date.today().year
for code in fetcher.METALS:
    print(code, len(fetcher._clean(fetcher._fetch_year(code, year))), "rows")
'@ | .venv\Scripts\python.exe -

Remove-Item Env:HC_PING_URL -ErrorAction SilentlyContinue
.venv\Scripts\python.exe -c "import healthcheck; healthcheck.ping_start(); healthcheck.ping_success('x'); healthcheck.ping_fail('y'); print('no-op OK')"
```

The closing `'@` must be at the very start of its line. Don't pass multi-line code to
`python -c` in PowerShell; its quoting mangles it. Pipe a here-string to `python -` instead.

## Line endings

The repo stores LF and has no `.gitattributes`. On Windows, `DataFrame.to_csv()` writes CRLF
(its default is `os.linesep`), so a local `fetcher.py` run rewrites every line of every CSV.

- With `core.autocrlf=true` (the Git for Windows default), Git converts CRLF back to LF when
  committing, so `git diff` shows only real data changes. "LF will be replaced by CRLF"
  warnings are harmless.
- If `git diff --stat data/` shows every line of every CSV changed, line endings are the
  cause. Don't commit that: run `git restore data/` and fix `core.autocrlf`.
- There's rarely a reason to commit CSVs from a local run, since the bot commits data daily.
  Discard local data changes with `git restore data/`.

## Testing

There is no test suite. After changing parsing, run the live check above for all metals.
After changing `healthcheck.py`, run the no-op ping check above.

## Git and CI

- `main` has linear history with no merge commits. Rebase or cherry-pick branches onto
  `main` instead of `git merge`.
- The bot commits `data: refresh YYYY-MM-DD` to `main` most days. Run `git pull --ff-only`
  before starting work and before pushing. If it refuses because you have local commits,
  use `git pull --rebase`.
- Pushing a change to `fetcher.py`, `healthcheck.py`, `requirements.txt` or the workflow starts
  a live refresh run, which commits data and pings Healthchecks.io. Docs-only pushes don't.
- Log user-visible changes in `CHANGELOG.md` under `[Unreleased]` (Keep a Changelog).
  Prefix docs-only commits with `docs:`.

## Rules

- Don't hand-edit `data/*.csv`; they're generated.
- Upstream columns are renamed by position, and `_check_layout()` guards their order. If
  westmetall changes its layout and the job fails, fix the parser; don't loosen the check.
- Monitoring must never break the job: `healthcheck.py` swallows its own errors and does
  nothing without `HC_PING_URL`. The real ping URL is a GitHub secret; never put it in code
  or logs.
- Be polite to westmetall.com: keep the 1-second sleep between pages and the `User-Agent`,
  and don't fetch in parallel.
- `requirements.txt` is pinned on purpose (pandas patch releases only). Bump versions
  deliberately and re-run the live check.

## Windows troubleshooting

- **`python3` or `python` opens the Microsoft Store or prints nothing.** That's a Windows
  app execution alias. Use `.venv\Scripts\python.exe` or `py -3.12`, or turn the aliases off
  in Settings → Apps → Advanced app settings → App execution aliases.
- **`Activate.ps1 cannot be loaded because running scripts is disabled`.** You don't need to
  activate; call `.venv\Scripts\python.exe` directly. To activate anyway, run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **pip tries to build pandas or lxml from source.** There's no prebuilt wheel for that
  Python. Recreate `.venv` with 64-bit CPython 3.12 (`py -3.12 -m venv .venv`).
- **`git push` asks for a username or password.** Run `gh auth setup-git`, or
  `gh auth login` again.
- **Every CSV shows as changed after a local run.** See [Line endings](#line-endings).
