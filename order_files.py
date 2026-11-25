import os
import shutil
import re
from datetime import datetime

def order_files(source_dir, dest_dir, start_id, skip_numbers):
    """
    Assigns sequential reference numbers to PDF files and moves
    them into the final destination directory.

    Files are grouped by date. Dates with only one file are
    assigned automatically. Dates with two or more files
    trigger an interactive prompt so the user can specify
    the exact ordering (e.g., "3 1 2").

    Example:
        Original: 04-06-2026 John Doe.pdf
        New:      R011 04-06-2026 John Doe.pdf

    Numbers included in skip_numbers are automatically skipped.
    """

    # ---------------------------------------------------------
    # STEP 1: MATCH STANDARDIZED FILENAMES
    # ---------------------------------------------------------

    # Every file in Sorted_Files/ follows the pattern
    # "<MM-DD-YYYY> <person>.pdf" because sort_files.py
    # enforces it.
    #
    # This regex extracts the date and person name separately.
    # Group 1 = date; Group 2 = person's name (without .pdf).
    NAME_PATTERN = re.compile(
        r'^(\d{2}-\d{2}-\d{4})\s+(.+)\.pdf$',
        re.IGNORECASE
    )

    # ---------------------------------------------------------
    # STEP 2: GROUP FILES BY DATE
    # ---------------------------------------------------------

    # groups maps each date string to a list of
    # (filename, person_name) tuples that share that date.
    # Using setdefault() creates the list on first access.
    groups = {}

    for filename in os.listdir(source_dir):

        if not filename.lower().endswith('.pdf'):
            continue

        match = NAME_PATTERN.match(filename)

        # Files that don't follow the standardized format were
        # not produced by sort_files.py (or were renamed manually).
        # Skip them so they don't break the ordering logic.
        if not match:
            print(f"Skipping (unrecognized format): {filename}")
            continue

        date_str = match.group(1)
        person = match.group(2)

        groups.setdefault(date_str, []).append((filename, person))

    # ---------------------------------------------------------
    # STEP 3: SORT DATES CHRONOLOGICALLY
    # ---------------------------------------------------------

    # Do NOT sort the date strings directly.
    # "01-15-2026" < "12-01-2025" alphabetically, which puts
    # the LATER date first when files span years.
    #
    # Instead, parse each date string into a real datetime
    # object before comparing. This gives true chronological
    # order across year boundaries.
    def _date_key(date_str):
        return datetime.strptime(date_str, "%m-%d-%Y")

    ordered_dates = sorted(groups.keys(), key=_date_key)

    # ---------------------------------------------------------
    # STEP 4: RESOLVE ORDER PER DATE GROUP
    # ---------------------------------------------------------

    # ordered_sequence accumulates every filename in its
    # FINAL sequence, ready for sequential ID assignment.
    ordered_sequence = []

    for date_str in ordered_dates:

        # Sort within the group alphabetically by person name
        # as a neutral default. The user can override this
        # in the next step if they want.
        group = sorted(groups[date_str], key=lambda x: x[1])

        # Single-file group → no prompt needed.
        if len(group) == 1:
            ordered_sequence.append(group[0][0])
            continue

        # -----------------------------------------------------
        # STEP 4a: DISPLAY THE GROUP
        # -----------------------------------------------------

        # Numbered list starting at 1, so the user can type
        # "3 1 2" and mean "file #3 first, then #1, then #2".
        print(f"\n=== {date_str} ({len(group)} files) ===")
        for i, (_, person) in enumerate(group, start=1):
            print(f"  {i}. {person}")

        # -----------------------------------------------------
        # STEP 4b: PROMPT AND VALIDATE INPUT
        # -----------------------------------------------------

        # Build an example string like "3 2 1" for the prompt.
        expected_count = len(group)
        example = " ".join(str(i) for i in range(expected_count, 0, -1))

        # Loop indefinitely until valid input is received.
        while True:

            try:
                raw = input(
                    f"Enter order (e.g. {example}): "
                )
            except (EOFError, KeyboardInterrupt):
                # Ctrl+C or Ctrl+D → abort cleanly.
                # No files have been moved yet at this point.
                print("\nAborted by user. No files were moved.")
                return

            # Empty input → explicitly invalid.
            # The user must provide a complete ordering.
            if not raw.strip():
                print(
                    f"ERROR: Input cannot be empty. "
                    f"Enter {expected_count} numbers."
                )
                continue

            # split() on whitespace handles extra spaces
            # gracefully: "3   1   2" → ["3", "1", "2"].
            parts = raw.split()

            # All parts must be integers.
            try:
                numbers = [int(p) for p in parts]
            except ValueError:
                print(
                    "ERROR: All entries must be integers "
                    "separated by spaces."
                )
                continue

            # Must have exactly as many numbers as files.
            if len(numbers) != expected_count:
                print(
                    f"ERROR: You must enter exactly "
                    f"{expected_count} numbers. "
                    f"Got {len(numbers)}."
                )
                continue

            # Must be a permutation of {1, 2, ..., N}.
            # The set comparison catches both duplicates
            # (e.g. "1 1 2") and out-of-range values
            # (e.g. "1 4 2").
            if set(numbers) != set(range(1, expected_count + 1)):
                print(
                    f"ERROR: Enter each number from 1 to "
                    f"{expected_count} exactly once."
                )
                continue

            # -------------------------------------------------
            # STEP 4c: APPLY THE REORDER
            # -------------------------------------------------

            # numbers[i] is a 1-based index into `group`.
            # numbers[i] - 1 converts to the 0-based Python index.
            #
            # Example: numbers = [3, 1, 2] with group
            # [Ash, Bash, Cash] yields [Cash, Ash, Bash].
            reordered = [group[n - 1][0] for n in numbers]
            ordered_sequence.extend(reordered)
            break

    # ---------------------------------------------------------
    # STEP 5: ASSIGN REFERENCE NUMBERS AND MOVE FILES
    # ---------------------------------------------------------

    current_id = start_id

    for filename in ordered_sequence:

        # Skip any ID in the skip list. The while loop (not if)
        # handles consecutive skips like [13, 15, 16]:
        # 13 → skip → 14 (ok), 15 → skip → 16 → skip → 17.
        while current_id in skip_numbers:
            print(f"--- Skipping ID: R{current_id:03d} (In skip array)")
            current_id += 1

        # :03d pads to three digits: 11 → "011", 156 → "156".
        formatted_id = f"R{current_id:03d}"
        new_filename = f"{formatted_id} {filename}"

        src_path = os.path.join(source_dir, filename)
        dst_path = os.path.join(dest_dir, new_filename)

        shutil.move(src_path, dst_path)
        print(f"Ordered: {filename} -> {new_filename}")

        current_id += 1

# -------------------------------------------------------------
# MAIN PROGRAM ENTRY POINT
# -------------------------------------------------------------

if __name__ == "__main__":

    SOURCE_DIR = "sortedFiles/"
    DEST_DIR = "orderedFiles/"
    
    # SOURCE_DIR = os.path.expanduser("~/Documents/sortedFiles/")
    # DEST_DIR = os.path.expanduser("~/Documents/orderedFiles/")

    # First ID to attempt. Skipped numbers still count as
    # "attempted" — e.g. with start_id=10 and skip=[13,15,16],
    # the first file may receive R010, and later files skip
    # 13, 15, and 16.
    STARTING_NUMBER = 56

    # IDs that must never be assigned.
    SKIP_ARRAY = [
        57, 59, 62, 63, 64, 65, 66, 67, 68, 71,
        74, 76, 77, 78, 79, 81, 82, 83, 84, 86,
        87, 89, 90, 105, 111, 112, 114, 115, 117, 118,
        122, 124, 132, 133, 150, 161, 167, 190, 197, 209,
        215, 221, 222, 232, 233, 234, 235, 236, 238, 239,
        240, 242, 243, 244, 254, 267, 273, 276, 277, 279,
        280, 282, 290, 293, 294, 296, 297, 299, 300, 301,
        302, 303, 304, 306, 307, 308, 309, 312, 313, 315,
        317, 318, 319, 320, 321, 323, 325, 326, 327, 328,
        330, 339, 340
    ]
    
    order_files(
        SOURCE_DIR,
        DEST_DIR,
        STARTING_NUMBER,
        SKIP_ARRAY
    )