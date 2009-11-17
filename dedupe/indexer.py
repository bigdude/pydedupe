"""
:mod:`indexer` -- Inverted index of records
===========================================

An inverted index lists records sharing an index key. By only comparing
pairs of records that share index keys the total number of comparisons
can be vastly reduced over the case of comparing all pairs of records.

.. module:: indexer
   :synopsis: Index records and carry out pairwise comparisons.
.. moduleauthor:: Graham Poulter

"""

from __future__ import with_statement

import logging
from compat import namedtuple, OrderedDict
import excel

class Index(dict):
    """Mapping from index key to records.
    
    :type makekey: function(record) [key,...]
    :param makekey: Generates the index keys for the record.    
    """
    
    def __init__(self, makekey):
        super(Index, self).__init__()
        self.makekey = makekey
        
    def insert(self, record):
        """Insert a record into the index.

        :type record: :class:`namedtuple`
        :param record: The record object to index.
        :rtype: [key,...]
        :return: Keys under which the record was inserted.
        """
        keys = self.makekey(record)
        assert isinstance(keys, tuple) or isinstance(keys, list) or isinstance(keys, set)
        for key in keys:
            if key is None or key == "":
                raise ValueError("Empty index key in %s" % repr(keys))
            recordsforkey = self.setdefault(key, list())
            recordsforkey.append(record)
        return keys
    
    def count_comparisons(self, other=None):
        """Upper bound on the number of comparisons required by this index.
        
        .. note:: comparisons are cached so the actual number of calls to the
           comparison function will in general be less than this.

        :type: other: :class:`Index` or :keyword:`None`
        :param other: Count comparisons against this index.
        :rtype: int
        :return: Most pairwise comparisons that need to be made.
        """
        comparisons = 0
        if not other or (other is self):
            # Count up comparisons to be made within this set of records.
            for recs in self.itervalues():
                if len(recs) > 1:
                    comparisons += len(recs)*(len(recs)-1)//2
        else:
            # Count up comparisons to be made to another set of records.
            for key in self:
                if key in other:
                    comparisons += len(self[key]) * len(other[key])
        return comparisons
    
    def link_self(self, compare, comparisons=None):
        """Perform dedupe comparisons on the index.  Note that this sorts
        the lists of records in each index key to ensure that rec1<rec2 
        in each resulting comparison tuple.
        
        :param compare: Comparison function
        :type compare: Function of record pair, returning vector of similarities.
        
        :param comparisons: Cache of comparisons, mapping (rec1,rec2)\
        to similarity vector, where rec1 < rec2.
        """
        if comparisons is None:
            comparisons = {}
        for indexkey, records in self.iteritems():
            records.sort()
            for j in range(len(records)):
                for i in range(j):
                    # i < j, and sorting means record[i] <= record[j]
                    a,b = records[i], records[j] 
                    # same record indexed under multiple keys!
                    if a is b: continue
                    # now compare a and b, keeping a <= b
                    if (a,b) not in comparisons:
                        comparisons[(a,b)] = compare(a,b)
        return comparisons
                        
    def link_other(self, other, compare, comparisons=None):
        """Perform linkage comparisons for this index against the other index.
        
        :param other: Index object against which to perform linkage comparison.
        
        :param compare: Function of two records returning a similarity vector\
        such as [0.3,0.8,1.0,...].
        
        :param comparisons: Cache of comparisons mapping (rec1,rec2) to\
        similarity vector. Inserted pairs will have rec1 from self and rec2\
        from other.
        """
        if comparisons is None:
            comparisons = {}
        for indexkey in self.iterkeys():
            if indexkey in other.iterkeys():
                for rec1 in self[indexkey]:
                    for rec2 in other[indexkey]:
                        pair = (rec1, rec2)
                        if pair not in comparisons:
                            comparisons[pair] = compare(*pair)
        return comparisons


class Indices(OrderedDict):
    """Represents a sever Index instances as an ordered dictionary.

    :type indices: (string, :class:`Index`)
    :param indices: Use these named indices.
    """

    def __init__(self, *indices):
        OrderedDict.__init__(self)
        for key, value in indices:
            self[key] = value
    
    def insert(self, records):
        """Insert records into each :class:`Index`."""
        for record in records:
            for index in self.itervalues():
                index.insert(record)
                

class RecordSim(OrderedDict):
    """Returns a vector of field value similarities between two records.

    :type comparators: [(string,:class:`sim.ValueSim`),...]
    :param comparators: Named, ordered field comparisons.
    
    :type Weights: :class:`namedtuple` (float,...)
    :ivar Weights: type of similarity vector between records\
      with field names corresponding to the names in `comparators`.
    
    :rtype: callable(R,R) :class:`Weights`
    :return: Compare two records using each value comparator in turn, giving\
      a vector of corresponding named similarity values.    
    """
    
    def __init__(self, *comparators):
        super(RecordSim, self).__init__(comparators)
        self.Weights = namedtuple("Weights", self.keys())

    def __call__(self, A, B):
        return self.Weights._make(
            comparator(A, B) for comparator in self.itervalues())
    
    def link_single_allpair(self, records):
        """Return comparisons for all distinct pairs of records.
        
        :type records: [R,...]
        :param records: records to compare
        :rtype: {(R,R):[float,...],...}
        :return: Similarity vectors for ordered pairs of compared records.
        """
        comparisons = {}
        for i in range(len(records)):
            for j in range(i):
                rec1, rec2 = records[i], records[j]
                pair = tuple(sorted([rec1,rec2]))
                if pair not in comparisons:
                    comparisons[pair] = self(rec1, rec2)
        return comparisons

    def link_pair_allpair(self, records1, records2):
        """Return comparisons for all distinct pairs of records.
        
        :type records1, records2: [R,...]
        :param records1, records2: records to compare
        :rtype: {(R1,R2):[float,...],...}
        :return: Similarity vectors for corresponding pairs of compared records.
        """
        comparisons = {}
        for i in range(len(records1)):
            for j in range(len(records2)):
                rec1, rec2 = records1[i], records2[j]
                pair = (rec1, rec2)
                if pair not in comparisons:
                    comparisons[pair] = self(rec1, rec2)
        return comparisons

    def link_single(self, indices):
        """Return comparisons against self for indexed records.
        
        :type indices: :class:`Indices`, {str:{obj:[R,...],...},...}
        :param indices: indexed left-hand records
        :rtype: {(R,R):[float,...],...}
        :return: Comparison similarity vectors for ordered pairs of compared records.
        """
        comparisons = {} # Map from (record1,record2) to L{Weights}
        for index in indices.itervalues():
            index.link_self(self, comparisons)
        return comparisons
    

    def link_pair(self, indices1, indices2):
        """Return comparisons between two sets of indexed records.

        :type indices1: :class:`Indices`, {str:{obj:[R,...],...},...}
        :param indices1: indexed left-hand records
        :type indices2: :class:`Indices`, {str:{obj:[R,...],...},...}
        :param indices2: indexed right-hand records
        :rtype: {(R,R):[float,...],...}
        :return: Similarity vectors for pairs of compared records.
        """
        assert indices1 is not indices2 # Must be different!
        comparisons = {}
        for index1, index2 in zip(indices1.itervalues(), indices2.itervalues()):
            index1.link_other(index2, self, comparisons)
        return comparisons

