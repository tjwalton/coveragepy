# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""Tests for coverage.numbits"""

import sqlite3

from hypothesis import example, given, settings
from hypothesis.strategies import sets, integers

from coverage import env
from coverage.numbits import (
    nums_to_numbits, numbits_to_nums, merge_numbits, numbits_any_intersection,
    num_in_numbits, register_sqlite_functions,
    )

from tests.coveragetest import CoverageTest

# Hypothesis-generated line number data
line_numbers = integers(min_value=1, max_value=9999)
line_number_sets = sets(line_numbers, min_size=1)

# When coverage-testing ourselves, hypothesis complains about a test being
# flaky because the first run exceeds the deadline (and fails), and the second
# run succeeds.  Disable the deadline if we are coverage-testing.
default_settings = settings()
if env.METACOV:
    default_settings = settings(default_settings, deadline=None)


class NumbitsOpTest(CoverageTest):
    """Tests of the numbits operations in numbits.py."""

    run_in_temp_dir = False

    @given(line_number_sets)
    @settings(default_settings)
    def test_conversion(self, nums):
        nums2 = numbits_to_nums(nums_to_numbits(nums))
        self.assertEqual(nums, set(nums2))

    @given(line_number_sets, line_number_sets)
    @settings(default_settings)
    def test_merging(self, nums1, nums2):
        merged = numbits_to_nums(merge_numbits(nums_to_numbits(nums1), nums_to_numbits(nums2)))
        self.assertEqual(nums1 | nums2, set(merged))

    @given(line_number_sets, line_number_sets)
    @settings(default_settings)
    def test_any_intersection(self, nums1, nums2):
        inter = numbits_any_intersection(nums_to_numbits(nums1), nums_to_numbits(nums2))
        expect = bool(nums1 & nums2)
        self.assertEqual(expect, bool(inter))

    @given(line_numbers, line_number_sets)
    @settings(default_settings)
    @example(152, {144})
    def test_num_in_numbits(self, num, nums):
        numbits = nums_to_numbits(nums)
        is_in = num_in_numbits(num, numbits)
        self.assertEqual(num in nums, is_in)


class NumbitsSqliteFunctionTest(CoverageTest):
    """Tests of the SQLite integration for numbits functions."""

    run_in_temp_dir = False

    def setUp(self):
        super(NumbitsSqliteFunctionTest, self).setUp()
        conn = sqlite3.connect(":memory:")
        register_sqlite_functions(conn)
        self.cursor = conn.cursor()
        self.cursor.execute("create table data (id int, numbits blob)")
        self.cursor.executemany(
            "insert into data (id, numbits) values (?, ?)",
            [
                (i, nums_to_numbits(range(i, 100, i)))
                for i in range(1, 11)
            ]
        )
        self.addCleanup(self.cursor.close)

    def test_merge_numbits(self):
        res = self.cursor.execute(
            "select merge_numbits("
                "(select numbits from data where id = 7),"
                "(select numbits from data where id = 9)"
                ")"
        )
        answer = numbits_to_nums(list(res)[0][0])
        self.assertEqual(
            [7, 9, 14, 18, 21, 27, 28, 35, 36, 42, 45, 49,
                54, 56, 63, 70, 72, 77, 81, 84, 90, 91, 98, 99],
            answer
        )

    def test_numbits_any_intersection(self):
        res = self.cursor.execute(
            "select numbits_any_intersection(?, ?)",
            (nums_to_numbits([1, 2, 3]), nums_to_numbits([3, 4, 5]))
        )
        answer = [any_inter for (any_inter,) in res]
        self.assertEqual([1], answer)

        res = self.cursor.execute(
            "select numbits_any_intersection(?, ?)",
            (nums_to_numbits([1, 2, 3]), nums_to_numbits([7, 8, 9]))
        )
        answer = [any_inter for (any_inter,) in res]
        self.assertEqual([0], answer)

    def test_num_in_numbits(self):
        res = self.cursor.execute("select id, num_in_numbits(12, numbits) from data order by id")
        answer = [is_in for (id, is_in) in res]
        self.assertEqual([1, 1, 1, 1, 0, 1, 0, 0, 0, 0], answer)
