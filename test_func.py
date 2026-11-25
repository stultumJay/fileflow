import unittest
import os
import shutil
import tempfile

# patch() from unittest.mock lets us replace builtins.input
# with a scripted sequence of responses during tests.
from unittest.mock import patch

# Imports must match the actual filenames of the two scripts.
from sort_files import sort_files
from order_files import order_files


class TestFileAutomation(unittest.TestCase):

    # ---------------------------------------------------------
    # STEP 1: PREPARE THE TEST ENVIRONMENT
    # ---------------------------------------------------------

    def setUp(self):
        # tempfile.mkdtemp() creates a unique throwaway folder
        # so multiple runs never interfere.
        self.test_dir = tempfile.mkdtemp()

        self.source_dir = os.path.join(self.test_dir, "files")
        self.sorted_dir = os.path.join(self.test_dir, "sortedFiles")
        self.ordered_dir = os.path.join(self.test_dir, "orderedFiles")

        os.makedirs(self.source_dir)
        os.makedirs(self.sorted_dir)
        os.makedirs(self.ordered_dir)

        # -----------------------------------------------------
        # STEP 2: DEFINE SAMPLE FILENAMES
        # -----------------------------------------------------

        # Five files, five DIFFERENT dates — no prompts will
        # fire in tests 1 and 2 because no same-date group
        # exceeds one file.
        #
        # IMPORTANT:
        # Use hyphens (-) instead of slashes (/) in dates.
        # Slashes are interpreted as directory separators by
        # the operating system and cause FileNotFoundError.
        #
        # NOTE: "Sept 06, 2026" uses a 4-letter abbreviation
        # that Python's %b rejects. sort_files.py must
        # normalize "Sept" → "Sep" before parsing. This test
        # therefore verifies that normalization works.
        self.sample_files = [
            "VR Jane Doe 04-20-2026.pdf",
            "VR John Doe 04-06-2026.pdf",
            "VR Samnuel Sept 6, 2026.pdf",
            "VR Jesus 06-10-2026.pdf",
            "VR Josh Doe - 12-10-2026.pdf"
        ]

        # -----------------------------------------------------
        # STEP 3: CREATE EMPTY DUMMY PDFs
        # -----------------------------------------------------

        # Empty .pdf files are enough — the scripts only
        # read filenames, never the file contents.
        for f in self.sample_files:
            with open(os.path.join(self.source_dir, f), 'w') as fp:
                pass

    # ---------------------------------------------------------
    # STEP 4: CLEAN UP AFTER TESTING
    # ---------------------------------------------------------

    def tearDown(self):
        # rmtree() recursively deletes the whole temp folder.
        shutil.rmtree(self.test_dir)

    # ---------------------------------------------------------
    # HELPER: REPLACE SAMPLE FILES WITH CUSTOM ONES
    # ---------------------------------------------------------

    def _reset_source_with(self, filenames):
        # Tests 3 and 4 need different inputs, so this helper
        # wipes the default samples and creates new ones.
        for f in os.listdir(self.source_dir):
            os.remove(os.path.join(self.source_dir, f))

        for f in filenames:
            with open(os.path.join(self.source_dir, f), 'w') as fp:
                pass

    # ---------------------------------------------------------
    # TEST 1: VERIFY FILE SORTING (SCRIPT 1)
    # ---------------------------------------------------------

    def test_1_sort_files(self):

        # Run the first script to sort and rename the files.
        sort_files(self.source_dir, self.sorted_dir)

        # Get the resulting filenames and sort alphabetically
        # so the order can be compared consistently.
        result_files = sorted(os.listdir(self.sorted_dir))

        # These are the filenames we expect after sorting.
        #
        # The "Sept 06, 2026" input must become "09-06-2026"
        # because sort_files.py normalizes "Sept" → "Sep"
        # before calling strptime. If it doesn't, the Samnuel
        # file will be missing here and the assertion below
        # will fail with "Second list contains 1 additional
        # elements" — a signal that the parser rejected the
        # date instead of the test being wrong.
        expected_files = [
            "04-06-2026 John Doe.pdf",
            "04-20-2026 Jane Doe.pdf",
            "06-10-2026 Jesus.pdf",
            "09-06-2026 Samnuel.pdf",
            "12-10-2026 Josh Doe.pdf"
        ]

        # Verify that the actual filenames match the expected
        # filenames exactly.
        self.assertEqual(
            result_files,
            expected_files,
            "Script 1 did not sort/rename correctly."
        )

    # ---------------------------------------------------------
    # TEST 2: VERIFY ORDERING WITH NO SAME-DATE GROUPS
    # ---------------------------------------------------------

    def test_2_order_files(self):

        # First, sort the original files using Script 1.
        sort_files(self.source_dir, self.sorted_dir)

        # No same-date collisions exist in the sample files,
        # so the interactive prompt should never fire.
        #
        # We patch input() defensively. If the script
        # unexpectedly calls it, the test will fail immediately.
        with patch(
            'builtins.input',
            side_effect=AssertionError(
                "input() was called unexpectedly — no same-date groups exist."
            )
        ):
            order_files(
                self.sorted_dir,
                self.ordered_dir,
                start_id=11,
                skip_numbers=[13, 15, 16]
            )

        # Retrieve the resulting filenames.
        result_files = sorted(os.listdir(self.ordered_dir))

        # Expected filenames after adding sequential IDs.
        # Numbers 13, 15, and 16 should be skipped.
        #
        # NOTE the R017 vs R018 placement: the Samnuel file
        # is 09-06-2026, which comes BEFORE 12-10-2026
        # chronologically. That's why Samnuel gets R017 and
        # Josh Doe gets R018, even though "Samnuel" sorts
        # alphabetically after "Josh".
        expected_files = [
            "R011 04-06-2026 John Doe.pdf",
            "R012 04-20-2026 Jane Doe.pdf",
            "R014 06-10-2026 Jesus.pdf",
            "R017 09-06-2026 Samnuel.pdf",
            "R018 12-10-2026 Josh Doe.pdf"
        ]

        # Verify that the files received the correct IDs.
        self.assertEqual(
            result_files,
            expected_files,
            "Script 2 did not prefix/order correctly."
        )

    # ---------------------------------------------------------
    # TEST 3: VERIFY SAME-DATE REORDERING
    # ---------------------------------------------------------

    def test_3_same_date_reordering(self):

        # Three files sharing one date → the prompt will fire.
        # Replace the default sample files with these files.
        self._reset_source_with([
            "VR Ash 04-01-2026.pdf",
            "VR Bash 04-01-2026.pdf",
            "VR Cash 04-01-2026.pdf",
        ])

        # Sort and rename the files before ordering them.
        sort_files(self.source_dir, self.sorted_dir)

        # Simulate the user typing "3 1 2" at the prompt.
        #
        # This means:
        # File #3 (Cash) goes first.
        # File #1 (Ash) goes second.
        # File #2 (Bash) goes third.
        #
        # patch() replaces input() so no actual user interaction
        # is needed while running the test.
        with patch('builtins.input', return_value='3 1 2'):
            order_files(
                self.sorted_dir,
                self.ordered_dir,
                start_id=10,
                skip_numbers=[]
            )

        # Retrieve the resulting filenames.
        result_files = sorted(os.listdir(self.ordered_dir))

        # If the reorder succeeded:
        # Cash receives R010.
        # Ash receives R011.
        # Bash receives R012.
        expected_files = [
            "R010 04-01-2026 Cash.pdf",
            "R011 04-01-2026 Ash.pdf",
            "R012 04-01-2026 Bash.pdf"
        ]

        # Verify that the custom ordering was applied correctly.
        self.assertEqual(
            result_files,
            expected_files,
            "Same-date reordering did not apply correctly."
        )

    # ---------------------------------------------------------
    # TEST 4: VERIFY REPROMPT ON INVALID INPUT
    # ---------------------------------------------------------

    def test_4_invalid_input_reprompt(self):

        # Replace the default files with three files sharing
        # the same date so the interactive prompt is triggered.
        self._reset_source_with([
            "VR Ash 04-01-2026.pdf",
            "VR Bash 04-01-2026.pdf",
            "VR Cash 04-01-2026.pdf",
        ])

        # Sort and rename the files before ordering them.
        sort_files(self.source_dir, self.sorted_dir)

        # side_effect feeds input() a SEQUENCE of responses,
        # one response for each call.
        #
        # The first two responses are intentionally invalid:
        #
        #   1st: "1 2"
        #        → Wrong length (only 2 numbers for 3 files).
        #
        #   2nd: "1 1 2"
        #        → Duplicate number (missing number 3).
        #
        #   3rd: "3 1 2"
        #        → Valid input, so the loop should exit.
        #
        # If the script fails to reprompt on invalid input,
        # this test will fail.
        inputs = ["1 2", "1 1 2", "3 1 2"]

        with patch('builtins.input', side_effect=inputs) as mock_input:
            order_files(
                self.sorted_dir,
                self.ordered_dir,
                start_id=10,
                skip_numbers=[]
            )

        # Retrieve the resulting filenames.
        result_files = sorted(os.listdir(self.ordered_dir))

        # Expected result after the third (valid) response.
        expected_files = [
            "R010 04-01-2026 Cash.pdf",
            "R011 04-01-2026 Ash.pdf",
            "R012 04-01-2026 Bash.pdf"
        ]

        # Verify that the valid input was eventually accepted
        # and that the files were reordered correctly.
        self.assertEqual(
            result_files,
            expected_files,
            "Reprompt-on-invalid-input did not work correctly."
        )

        # Verify that input() was called exactly three times:
        # two invalid attempts followed by one valid attempt.
        self.assertEqual(
            mock_input.call_count,
            3,
            "The program did not reprompt the expected number of times."
        )


# -------------------------------------------------------------
# MAIN TEST EXECUTION
# -------------------------------------------------------------

# This allows the test file to be executed directly using:
# python test_func.py
if __name__ == '__main__':
    unittest.main()