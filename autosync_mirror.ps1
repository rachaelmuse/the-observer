# ============================================================================
# Observer Mirror Autosync - daily snapshot to the PRIVATE mirror only.
#
# House-law reconciliation (archive_ledger_local.ps1): that script declares
# the audit ledger LOCAL-ONLY because the public repo must never see it, and
# therefore refuses to git-commit. This script upholds the same law:
#   - data/ (ledger, db, archive, logs) is gitignored and NEVER staged
#   - pushes go ONLY to `mirror` (rachaelmuse/the-observer_private)
#   - the public `origin` is NEVER touched by automation
# User directive Sep 10: auto-commit + auto-push the mirror daily.
#
# Behavior:
#   - clean tree  -> silent no-op (log line only)
#   - dirty tree  -> stage all -> SECRET GATE -> commit -> push mirror
#   - gate hit    -> ABORT, unstage, log filenames (values never logged)
#   - push fail   -> work stays committed locally; next run pushes it
# Log: data\autosync.log (ignored path; rotates itself past 256 KB)
# ============================================================================

$repo = 'D:\The_Observer'
$logDir = Join-Path $repo 'data'
$log = Join-Path $logDir 'autosync.log'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Log($msg) {
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    if ((Test-Path $log) -and ((Get-Item $log).Length -gt 256KB)) {
        $tail = Get-Content $log -Tail 200
        Set-Content -Path $log -Value $tail
    }
    Add-Content -Path $log -Value "$stamp $msg"
}

if (-not (Test-Path (Join-Path $repo '.git'))) { exit 1 }
Push-Location $repo

# 0. never fight a running git process (Observer desk may be working)
if (Test-Path (Join-Path $repo '.git\index.lock')) { Log 'SKIP: index.lock present'; Pop-Location; exit 0 }

# 1. anything to do?
$st = git status --porcelain
if (-not $st) { Log 'no-op: tree clean'; Pop-Location; exit 0 }
$dirty = ($st | Measure-Object).Count

# 2. stage everything (gitignore already walls off data/, caches, venvs)
git add -A 2>$null
if ($LASTEXITCODE -ne 0) { Log "FAIL: git add exit $LASTEXITCODE"; Pop-Location; exit 1 }

# 3. SECRET GATE over the exact staged set (filenames only; values never logged)
# NOTE: pattern must contain NO quote characters - PS 5.1 mangles native args
# containing quotes, which breaks the pathspec below and makes the gate scan
# its own script. '.' stands in for the quote position in the char class.
$patterns = 'sk-[A-Za-z0-9_-]{20}|ghp_[A-Za-z0-9]{20}|github_pat_|AKIA[0-9A-Z]{16}|xox[baprs]-|BEGIN [A-Z ]*PRIVATE KEY|api[_-]?key[ ]*[:=][ ]*.[A-Za-z0-9+/_-]{16}'
$hits = git grep --cached -l -E $patterns -- ':(exclude)autosync_mirror.ps1' 2>$null
if ($hits) {
    Log ("ABORT: secret gate hit -> unstaged, NOT committed: " + ($hits -join ' | '))
    git reset 2>$null | Out-Null
    Pop-Location
    exit 2
}

# 4. commit
$msg = "autosync: daily snapshot $stamp ($dirty path(s))"
git commit -m $msg 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Log "FAIL: commit exit $LASTEXITCODE"; Pop-Location; exit 1 }

# 5. push to the PRIVATE mirror only (stderr is normal git progress; exit code rules)
$pushOut = cmd /c 'git push mirror main 2>&1'
if ($LASTEXITCODE -ne 0) {
    Log "WARN: push to mirror failed (exit $LASTEXITCODE) - work committed locally, next run retries"
    Pop-Location
    exit 1
}

$h = git rev-parse --short HEAD
Log "OK: $h committed ($dirty path(s)) + pushed to mirror"
Pop-Location
exit 0
