import os
import shutil
import re
from datetime import datetime

def sort_files(source_dir, dest_dir):
    """
    Organizes PDF files by extracting the date and person's name
    from each filename.

    The date is standardized to MM-DD-YYYY, and the person's name
    is placed after the date.

    Example:
        Original: VR Jane Doe 04/20/2026.pdf
        New:      04-20-2026 Jane Doe.pdf

    Files without a recognizable or valid date are logged and skipped.
    """

    # ---------------------------------------------------------
    # STEP 1: DEFINE THE DATE DETECTION PATTERN
    # ---------------------------------------------------------

    # Regex matches two date shapes:
    #   1. Numeric: 04/20/2026, 04-20-2026, 12-10-26
    #   2. Written month: Sept 06, 2026, September 06, 2026
    #
    # (?P<date>...) is a named group, retrievable via
    # match.group('date') instead of positional indexing.
    DATE_PATTERN = re.compile(
        r'(?P<date>'
        r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
        r'|'
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
        r')',
        re.IGNORECASE
    )

    # ---------------------------------------------------------
    # STEP 2: DEFINE THE DATE FORMATS WE CAN CONVERT
    # ---------------------------------------------------------

    # Regex detects the date, but Python needs to know how
    # to interpret it. Each format string below matches one
    # layout we support.
    #
    # NOTE: Python's %b accepts "Sep" but NOT "Sept". The
    # parser therefore normalizes "Sept" -> "Sep" before
    # trying these formats (see STEP 7).
    DATE_FORMATS = [
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%m-%d-%y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y"
    ]

    # ---------------------------------------------------------
    # STEP 3: READ THE SOURCE DIRECTORY
    # ---------------------------------------------------------

    for filename in os.listdir(source_dir):

        # Process PDFs only. lower() makes the check
        # case-insensitive so .PDF/.Pdf also match.
        if not filename.lower().endswith('.pdf'):
            continue

        # -----------------------------------------------------
        # STEP 4: SEPARATE FILENAME FROM EXTENSION
        # -----------------------------------------------------

        # splitext() splits "VR Jane Doe 04/20/2026.pdf" into
        # name_without_ext = "VR Jane Doe 04/20/2026"
        # ext              = ".pdf"
        name_without_ext, ext = os.path.splitext(filename)

        # Strip "VR " only if present at the start.
        # [3:] means "start at character index 3 onward",
        # effectively removing the first three characters.
        clean_name = (
            name_without_ext[3:]
            if name_without_ext.startswith("VR ")
            else name_without_ext
        )

        # -----------------------------------------------------
        # STEP 5: SEARCH FOR THE DATE
        # -----------------------------------------------------

        # search() scans anywhere in the filename, not just the start.
        match = DATE_PATTERN.search(clean_name)

        # No date → cannot safely rename → skip with a log message.
        if not match:
            print(f"Skipping (no date found): {filename}")
            continue

        # Retrieve the exact date string the regex matched.
        # Example: "04/20/2026" or "Sept 06, 2026".
        date_str = match.group('date')

        # -----------------------------------------------------
        # STEP 6: EXTRACT THE PERSON'S NAME
        # -----------------------------------------------------

        # The person's name sits BEFORE the date.
        # split(date_str)[0] grabs everything before the date.
        # strip(' -') removes stray spaces/hyphens from either end.
        name_part = clean_name.split(date_str)[0].strip(' -')

        # -----------------------------------------------------
        # STEP 7: NORMALIZE NON-STANDARD ABBREVIATIONS
        # -----------------------------------------------------

        # Python's strptime with %b accepts "Sep" but rejects
        # "Sept" — a common real-world spelling. The following
        # substitution maps "Sept" (as a whole word) to "Sep"
        # so the parser accepts it. \b ensures we don't rewrite
        # "September" (which %B already handles natively).
        date_str_normalized = re.sub(
            r'(?i)\bSept\b',
            'Sep',
            date_str
        )

        # -----------------------------------------------------
        # STEP 8: CONVERT THE EXTRACTED DATE INTO A DATETIME
        # -----------------------------------------------------

        # parsed_date stays None until a format succeeds.
        parsed_date = None

        # Try each supported format; the first one that works wins.
        # strptime() raises ValueError on mismatch → try next format.
        for fmt in DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_str_normalized, fmt)
                break
            except ValueError:
                continue

        # -----------------------------------------------------
        # STEP 9: STANDARDIZE THE DATE AND BUILD THE NEW FILENAME
        # -----------------------------------------------------

        if parsed_date:

            # strftime("%m-%d-%Y") → always MM-DD-YYYY.
            # Example: 4/20/2026 becomes 04-20-2026.
            formatted_date = parsed_date.strftime("%m-%d-%Y")

            # Final format: "<MM-DD-YYYY> <person-name>.pdf"
            new_filename = f"{formatted_date} {name_part}{ext}"

            # -------------------------------------------------
            # STEP 10: BUILD SOURCE AND DESTINATION PATHS
            # -------------------------------------------------

            src_path = os.path.join(source_dir, filename)
            dst_path = os.path.join(dest_dir, new_filename)

            # -------------------------------------------------
            # STEP 11: MOVE AND RENAME THE FILE
            # -------------------------------------------------

            # shutil.move() handles cross-directory moves and
            # renames in a single operation. The original file
            # is removed from the source directory on success.
            shutil.move(src_path, dst_path)

            print(f"Sorted: {filename} -> {new_filename}")

        else:
            # -------------------------------------------------
            # STEP 12: LOG UNPARSEABLE DATES (CRITICAL)
            # -------------------------------------------------

            # Without this branch, files disappear silently when
            # the regex matches but the date can't be parsed.
            # This message lets you spot data issues immediately.
            print(
                f"Skipping (date not parseable): {filename} "
                f"(regex matched: '{date_str}')"
            )

# -------------------------------------------------------------
# MAIN PROGRAM ENTRY POINT
# -------------------------------------------------------------

if __name__ == "__main__":

    SOURCE_DIR = "files/"
    DEST_DIR = "sortedFiles/"

    sort_files(SOURCE_DIR, DEST_DIR)