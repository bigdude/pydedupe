"""
:mod:`sim.dale` -- Damerau-Levenshtein string distance
==============================================================

Implementation of Damerau-Levenshtein distance by `mwh.geek.nz`_::

   The Damerau-Levenshtein distance between two strings is the number of
   additions, deletions, substitutions, and transpositions needed to transform
   one into the other. It's an extension of the Levenshtein distance, 
   by incorporating transpositions into the set of operations.

   I had a need to use it in a program recently, but I couldn't find any Python
   implementation around that wasn't trivially buggy or horrendously
   inefficient (strictly, you can implement it neatly by recursion, and it's
   instructive for examining the algorithm, but it takes an age to run when you
   do). I've put one together myself from the algorithmic definition that
   I've tested to work correctly and reasonably efficiently.

   The algorithm is inherently O(N*M) in time, and the naive version is in space
   as well. This implementation is O(M) in space, as only the last two rows of th

   The code is available under the MIT licence, in the hope that it will be
   useful, but without warranty of any kind. I have also included a codesnippet
   GUID in line with the linked post, as a sort of experiment. Please leave that
   comment intact if you're posting a derivative somewhere, and add your own.

.. _`mwh.geek.nz`: http://mwh.geek.nz/2009/04/26/python-damerau-levenshtein-distance/

.. moduleauthor:: mwh.geek.nz
"""

from __future__ import division

__license__ = "MIT"

def distance(seq1, seq2):
    """Return Damerau-Levenshtein distance between sequences.

    This distance is the number of additions, deletions, substitutions, and
    transpositions needed to transform the first sequence into the second.
    Although generally used with strings, any sequences of comparable objects
    will work. Transpositions are exchanges of *consecutive* characters.

    This implementation is O(N*M) time and O(M) space, for N and M the
    lengths of the two sequences.
    
    :param seq1, seq2: sequences to compare
    :type seq1, seq2: any sequence type

    >>> distance("abcd","ab")
    2
    >>> distance("abcd","abdc")
    1
    >>> distance("dbca","abcd")
    2
    """
    # codesnippet:D0DE4716-B6E6-4161-9219-2903BF8F547F
    # Conceptually, this is based on a len(seq1) + 1 * len(seq2) + 1 matrix.
    # However, only the current and two previous rows are needed at once,
    # so we only store those.
    oneago = None
    thisrow = range(1, len(seq2) + 1) + [0]
    for x in xrange(len(seq1)):
        # Python lists wrap around for negative indices, so put the
        # leftmost column at the *end* of the list. This matches with
        # the zero-indexed strings and saves extra calculation.
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
        for y in xrange(len(seq2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (seq1[x] != seq2[y])
            thisrow[y] = min(delcost, addcost, subcost)
            # This block deals with transpositions
            if (x > 0 and y > 0 and seq1[x] == seq2[y-1]
                and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
                thisrow[y] = min(thisrow[y], twoago[y-2] + 1)
    return thisrow[len(seq2) - 1]

def compare(maxdiff, s1, s2, missing=None):
    """Return similarity of strings based on Damerau-Levenshtein distance.
    
    :type maxdiff: :class:`float` in 0.0 to 1.0
    :param maxdiff: proportion of ``max(len(s1),len(s2))`` beyond which\
       the similarity is considered similarity of 0. Higher values are more lenient.
    :param missing: return this if one string is empty or :keyword:`None`
    :rtype: :class:`float`
    :return: similarity between 0.0 and 1.0.
    
    >>> compare(1.0, "abcd","abcd")
    1.0
    >>> compare(1.0, "abcd","abdc")
    0.75
    >>> compare(1.0, "abcd","") is None
    True
    >>> compare(0.5, "abcd","badc")
    0.0
    >>> compare(1.0, "abcdef","abcd")
    0.66666666666666674
    >>> compare(0.5, "abcdef","abcd")
    0.33333333333333337
    """
    from levenshtein import _compare
    return _compare(maxdiff, s1, s2, missing, distance)

if __name__=="__main__":
    import sys
    print distance(sys.argv[1],sys.argv[2])
