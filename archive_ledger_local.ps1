# Observer auto-archive — weekly scheduled job (task name: "Observer Ledger Archive").
# LOCAL-ONLY by law: the_observer GitHub repo is PUBLIC, and the audit ledger
# (data/observer.db) must never leave this machine. This script snapshots the
# SQLite ledger into D:\Observer_Ledger_Archive and keeps the newest 8.
# It does NOT git-commit: the observer repo's working tree belongs to its own desk.
$ErrorActionPreference = 'Continue'
$src = 'D:\The_Observer\data\observer.db'
$destDir = 'D:\Observer_Ledger_Archive'
$log = 'D:\The_Observer\archive_ledger_local.log'
$keep = 8

function Log($m) {
    Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
}

Log 'run start'

if (-not (Test-Path $src)) {
    Log "SNAPSHOT FAILED - source missing: $src"
} else {
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'   # lowercase mm/ss: MM is MONTH in PS format strings
    $dest = Join-Path $destDir "observer_$stamp.db"
    try {
        Copy-Item -Path $src -Destination $dest -Force
        Log ("snapshot ok: {0} ({1} bytes)" -f $dest, (Get-Item $dest).Length)
    } catch {
        Log ("SNAPSHOT FAILED: {0}" -f $_.Exception.Message)
    }
    # Prune: keep newest $keep snapshots.
    $old = @(Get-ChildItem -Path $destDir -Filter 'observer_*.db' |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip $keep)
    foreach ($f in $old) {
        Remove-Item -Path $f.FullName -Force
        Log ("pruned old snapshot: {0}" -f $f.Name)
    }
}

Log 'run end'
