import os
import shutil
import sys
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path

APPLIED = Path(r"C:\Work\Dream Chamber\Personal\Job Search\Applications\Applied")
GHOSTED = Path(r"C:\Work\Dream Chamber\Personal\Job Search\Applications\Ghosted")
GHOST_AFTER_DAYS = 30


def parse_folder_date(name):
    try:
        return datetime.strptime(name, "%Y-%m-%d").date()
    except ValueError:
        return None

def is_ghosted(folder_date, today):
    return (today - folder_date).days > GHOST_AFTER_DAYS

def find_ghosted(applied_dir, today):
    files = []
    folders = sorted(os.listdir(applied_dir))

    for folder in folders:
        full_folder_path = applied_dir / folder
        if not os.path.isdir(full_folder_path):
            continue

        folder_date = parse_folder_date(folder)
        if folder_date is None:
            continue

        if not is_ghosted(folder_date, today):
            continue

        files.append(full_folder_path)

    return files

def move_folder(src, ghosted_dir, dry_run, verbose = False):
    if os.path.exists(ghosted_dir):
        return "Skipped"

    if not dry_run:
        shutil.move(src, ghosted_dir)

    if verbose:
        print(f"{'Would move' if dry_run else 'Moved'} {src.name}")

    return None

def main():
    print(f"SCRIPT RAN ON: {date.today()}")
    dry_run = "--dry-run" in sys.argv
    skipped_files = []
    files = find_ghosted(APPLIED, date.today())
    if not files: print("Nothing to move")

    for ghosted_folders in files:
        if move_folder(ghosted_folders, os.path.join(GHOSTED, Path(ghosted_folders).name), dry_run, True) == "Skipped":
            skipped_files.append(Path(ghosted_folders).name)

    if skipped_files:
        print("The following files were skipped:")
        for file in skipped_files:
            print(f"Skipped {file} (already in Ghosted)")

    print("================")


def self_check():
    """Runs before every real run. Any failed assert stops the script before it touches real folders."""
    today = date(2026, 10, 15)

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
    self_check()
    main()