# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""
Functions to manipulate packed binary representations of number sets.

To save space, coverage stores sets of line numbers in SQLite using a packed
binary representation called a numbits.  A numbits is stored as a blob in the
database.  The exact meaning of the bytes in the blobs should be considered an
implementation detail that might change in the future.  Use these functions to
work with those binary blobs of data.

"""

from coverage import env
from coverage.backward import byte_to_int, bytes_to_ints, binary_bytes, zip_longest
from coverage.misc import contract, new_contract

if env.PY3:
    def to_blob(b):
        """Convert a bytestring into a type SQLite will accept for a blob."""
        return b

    new_contract('blob', lambda v: isinstance(v, bytes))
else:
    def to_blob(b):
        """Convert a bytestring into a type SQLite will accept for a blob."""
        return buffer(b)                                    # pylint: disable=undefined-variable

    new_contract('blob', lambda v: isinstance(v, buffer))   # pylint: disable=undefined-variable

@contract(nums='Iterable', returns='blob')
def nums_to_numbits(nums):
    """Convert `nums` (a non-empty iterable of ints) into a numbits."""
    nbytes = max(nums) // 8 + 1
    b = bytearray(nbytes)
    for num in nums:
        b[num//8] |= 1 << num % 8
    return to_blob(bytes(b))

@contract(numbits='blob', returns='list[int]')
def numbits_to_nums(numbits):
    """Convert a numbits into a list of numbers."""
    nums = []
    for byte_i, byte in enumerate(bytes_to_ints(numbits)):
        for bit_i in range(8):
            if (byte & (1 << bit_i)):
                nums.append(byte_i * 8 + bit_i)
    return nums

@contract(numbits1='blob', numbits2='blob', returns='blob')
def merge_numbits(numbits1, numbits2):
    """Merge two numbits"""
    byte_pairs = zip_longest(bytes_to_ints(numbits1), bytes_to_ints(numbits2), fillvalue=0)
    return to_blob(binary_bytes(b1 | b2 for b1, b2 in byte_pairs))

@contract(numbits1='blob', numbits2='blob', returns='bool')
def numbits_any_intersection(numbits1, numbits2):
    """Is there any number that appears in both numbits?"""
    byte_pairs = zip_longest(bytes_to_ints(numbits1), bytes_to_ints(numbits2), fillvalue=0)
    return any(b1 & b2 for b1, b2 in byte_pairs)

@contract(num='int', numbits='blob', returns='bool')
def num_in_numbits(num, numbits):
    """Does the integer `num` appear in `numbits`?"""
    nbyte, nbit = divmod(num, 8)
    if nbyte >= len(numbits):
        return False
    return bool(byte_to_int(numbits[nbyte]) & (1 << nbit))

def register_sqlite_functions(connection):
    """
    Define numbits functions in a SQLite connection.

    This defines these functions for use in SQLite statements:

    * merge_numbits
    * numbits_any_intersection
    * num_in_numbits

    """
    connection.create_function("merge_numbits", 2, merge_numbits)
    connection.create_function("numbits_any_intersection", 2, numbits_any_intersection)
    connection.create_function("num_in_numbits", 2, num_in_numbits)
