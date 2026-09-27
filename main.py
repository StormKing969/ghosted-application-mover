"""Ghosted application mover.

Moves job-application date folders from Applied/ to Ghosted/ once they're more than
GHOST_AFTER_DAYS old with no reply. Each date folder moves whole, apps and all:

    Applied/2026-09-06/Acme - SWE/   ->   Ghosted/2026-09-06/Acme - SWE/

Usage:
    python main.py              move for real
    python main.py --dry-run    only print what would move

Runs on the 1st and 15th via Windows Task Scheduler (task "\\Dream Chamber\\Ghosted
Application Mover"), which appends the output to ghosted.log.
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path

APPLIED = Path(r"C:\Work\Dream Chamber\Personal\Job Search\Applications\Applied")
GHOSTED = Path(r"C:\Work\Dream Chamber\Personal\Job Search\Applications\Ghosted")
GHOST_AFTER_DAYS = 30  # a folder must be MORE than this many days old to move


def parse_folder_date(name):
    """Turn a folder name like '2026-09-06' into a date. Return None if it isn't one."""
    try:
        return datetime.strptime(name, "%Y-%m-%d").date()
    except ValueError:
        return None

def is_ghosted(folder_date, today):
    """True if folder_date is more than GHOST_AFTER_DAYS before today.

    `today` is passed in rather than read inside, so self_check can test with fixed dates.
    """
    return (today - folder_date).days > GHOST_AFTER_DAYS

def find_ghosted(applied_dir, today):
    """Return full paths of the date folders in applied_dir that are old enough to move, oldest first.

    Only looks at the top level (the date folders). Never looks inside them, because
    the whole date folder moves as one.
    The date comes from the folder NAME, not its modified time: adding an app to a
    folder updates its modified time, but the name is the day you applied.
    """
    files = []
    folders = sorted(os.listdir(applied_dir))  # ISO dates sort oldest -> newest

    for folder in folders:
        full_folder_path = applied_dir / folder
        # skip stray files, even one named like a date
        if not os.path.isdir(full_folder_path):
            continue

        # skip folders that aren't dates, e.g. "misc"
        folder_date = parse_folder_date(folder)
        if folder_date is None:
            continue

        if not is_ghosted(folder_date, today):
            continue

        files.append(full_folder_path)

    return files

def move_folder(src, ghosted_dir, dry_run, verbose = False):
    """Move the date folder `src` to `ghosted_dir`, which is the full target path
    (e.g. Ghosted/2026-09-06), not the Ghosted folder itself.

    Returns "Skipped" if the target already exists, otherwise None.
    With dry_run, nothing moves; it only reports what would.
    """
    # Without this check, shutil.move would nest the folder inside the existing one:
    # Ghosted/2026-09-06/2026-09-06. Skip it and let a human merge them.
    if os.path.exists(ghosted_dir):
        return "Skipped"

    if not dry_run:
        shutil.move(src, ghosted_dir)

    # print after the move, so a failed move never claims "Moved"
    if verbose:
        print(f"{'Would move' if dry_run else 'Moved'} {src.name}")

    return None

def main():
    """Find the old date folders in Applied/ and move them to Ghosted/, printing what happened.

    The output is the only record of a scheduled run: Task Scheduler appends it to ghosted.log.
    """
    print(f"SCRIPT RAN ON: {date.today()}")  # separates runs in ghosted.log
    dry_run = "--dry-run" in sys.argv
    skipped_files = []
    files = find_ghosted(APPLIED, date.today())
    # say so explicitly, so an empty run doesn't look like the script never ran
    if not files: print("Nothing to move")

    for ghosted_folders in files:
        # target = Ghosted/<same date folder name>
        if move_folder(ghosted_folders, os.path.join(GHOSTED, Path(ghosted_folders).name), dry_run, True) == "Skipped":
            skipped_files.append(Path(ghosted_folders).name)

    if skipped_files:
        print("The following files were skipped:")
        for file in skipped_files:
            print(f"Skipped {file} (already in Ghosted)")

    print("================")


def self_check():
    """Runs before every real run. Any failed assert stops the script before it touches real folders."""
    today = date(2026, 10, 15)  # fixed "today" so the results never depend on when this runs

    assert parse_folder_date("2026-09-06") == date(2026, 9, 6)
    assert parse_folder_date("misc") is None
    assert parse_folder_date("2026-13-40") is None

    # strictly more than GHOST_AFTER_DAYS
    assert is_ghosted(today - timedelta(days=31), today)
    assert not is_ghosted(today - timedelta(days=30), today)
    assert not is_ghosted(today - timedelta(days=29), today)

    # find + move against a throwaway folder tree, never the real one
    with tempfile.TemporaryDirectory() as tmp:
        applied = Path(tmp) / "Applied"
        ghosted = Path(tmp) / "Ghosted"
        (applied / "2026-09-01" / "Acme - SWE").mkdir(parents=True)  # old -> should move
        (applied / "2026-10-10").mkdir()                             # recent -> stays
        (applied / "misc").mkdir()                                   # not a date -> ignored
        (applied / "2026-08-01").touch()                             # a FILE with a date name -> ignored
        ghosted.mkdir()

        found = find_ghosted(applied, today)
        assert found == [applied / "2026-09-01"], found

        src = found[0]
        target = ghosted / src.name

        assert move_folder(src, target, dry_run=True) != "Skipped"
        assert src.exists() and not target.exists(), "dry run must not move anything"

        assert move_folder(src, target, dry_run=False) != "Skipped"
        assert not src.exists() and (target / "Acme - SWE").exists()

        # target already exists -> skip and leave the source alone
        src.mkdir()
        assert move_folder(src, target, dry_run=False) == "Skipped"
        assert src.exists()


if __name__ == "__main__":
    self_check()  # a failed assert raises here, so main() never runs
    main()