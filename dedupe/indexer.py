"""Inverted index of records, and comparator of records that can use
an inverted index to reduce the required number of comparisons.

Record ID is always assumed to be the first field of a record.

@author: Graham Poulter
@copyright: MIH Holdings
@license: GPL
"""

from __future__ import with_statement

from operator import attrgetter
from UserDict import UserDict
import csv, logging
from compat import namedtuple, OrderedDict

def getfield(record, field):
    """Retrieve a field from a record. The field may be specified with an
    integer (index), string (attribute name), or a function (applied to the
    record).

    This works whether the record is a tuple (use integer index), an
    object or named tuple (use attribute lookup), or we are computing the field
    value from the record (use function of the record).  
    
    The return value could be a string, integer, or a set of values, or
    whatever the field function returns.
    """
    if isinstance(field, str):
        return record.__getattribute__(field)
    elif isinstance(field, int):
        return record[field]
    elif hasattr(field, "__call__"):
        return field(record)
    else:
        raise ValueError("Could not locate field %s in %s", str(field), str(record))

    

class Index(dict):
    """A dictionary from index key to the set of unique records sharing tha
    index key. The index key is automatically created by the key-making
    function on insertion of the record."""
    
    def __init__(self, makekey):
        """Parameterise the Index. 
        
        @param makekey: Function from record tuple -> to string of index key,
        or a tuple of index keys for the record.
        """
        super(Index, self).__init__()
        self.makekey = makekey
        
    def insert(self, record):
        """Index a record by its keys.
        
        @param: The record to index.
        @return: The key with which the record was inserted.
        """
        keys = self.makekey(record)
        # makekey might return a single key or a sequence of keys
        if not (isinstance(keys, tuple) or isinstance(keys, list)): 
            keys = (keys,)
        for key in keys:
            if key: # Skip over non-keys like "", 0, None
                recordsforkey = self.setdefault(key, set())
                recordsforkey.add(record)
        return keys
    
    def count_comparisons(self, other=None):
        """Count the number of comparisons implied by the index.

        @param other: An optional Index instance to compare this one against.
        
        @return: Total number of comparisons that need to be made.
        """
        result = 0
        if other is self or other is None:
            # Count up comparisons to be made within this set of records.
            for recs in self.itervalues():
                if len(recs) > 1:
                    result += len(recs)*(len(recs)-1)//2
        else:
            # Count up comparisons to be made to another set of records.
            for key in self:
                if key in other:
                    result += len(self[key]) * len(other[key])
        return result

    
class Indeces(OrderedDict):
    """Represents multiple Index instances as an ordered dictionary."""

    def __init__(self, *indeces):
        """Takes a number of (indexname, index) pairs as arguments."""
        OrderedDict.__init__(self)
        for key, value in indeces:
            self[key] = value
    
    def insert(self, records):
        """Insert the iteration of records in each Index."""
        for record in records:
            for index in self.itervalues():
                index.insert(record)
                
    def log_index_stats(self, other=None, log=None):
        """Log statistics and expected number of comparisons about the indeces."""
        if other is None:
            other = self
        if log is None:
            log = logging.getLogger()
        for (i1name, index1), (i2name, index2) in zip(self.items(), other.items()): # Pairs of corresponding indeces
            num_comparisons = index1.count_comparisons(index2)
            log.info("Comparing %s to %s needs %d comparisons.", i1name, i2name, num_comparisons)
        for indeces in [ (self, other) if other is not self else self ]:
            for indexname, index in indeces.iteritems(): 
                if index:
                    nrecords = sum(len(recs) for recs in index.itervalues())
                    biggroup = max(len(recs) for recs in index.itervalues())
                    nkeys = len(index)
                    log.info("%s has %d keys, %d records. Largest block: %d, Average: %.2f",
                             indexname, nkeys, nrecords, biggroup, float(nrecords)/nkeys)
            
    def write_indeces(self, basepath):
        """Write the contents of the index dictionaries in CSV format."""
        for indexname, index in self.iteritems():
            with open(basepath + indexname + ".csv", "w") as stream:
                writer = csv.writer(stream)
                for indexkey, rows in index.iteritems():
                    for row in rows:
                        writer.writerow((indexkey,) + row)

class ValueComparator(object):
    """Defines a callable comparison of a pair of records on a defined field.
    
    @ivar comparevalues: Function to compare the computed, encoded field values.
    @ivar field1: Field specifier applied to the first record.
    @ivar encode1: Function to encode field values from the first record.
    @ivar field2: Field specifier applied to the second record (default is field1).
    @ivar encode2: Function to encode field values from second record (default is encode1).
    
    @note: The L{field1} and L{field2} specifiers may be an integer index into the record, 
    a string key or attribute to look up in the record, or in the most general
    case a function applied to the record to compute a field value.
    
    @note: The L{encode1} and L{encode2} functions transform the retrieved field values
    just prior to comparison, for example to remove spaces and fold case.  Each
    accepts one paramenter of the type returned by the corresponding field
    parameter, and returns a value suitable for comparevalues.
    
    @note: The L{comparevalues} function takes two parameters, of the
    value types returned by encode1 and encode2 respectively. 
    """
    
    def __init__(self, comparevalues, field1, encode1=lambda x:x, field2=None, encode2=None):
        """Initialise field comparison object"""
        self.comparevalues = comparevalues
        self.field1 = field1
        self.encode1 = encode1
        self.field2 = field2 or field1
        self.encode2 = encode2 or encode1

    def __call__(self, record1, record2):
        """Compare the two records on the defined fields."""
        return self.comparevalues(
            self.encode1(getfield(record1, self.field1)), 
            self.encode2(getfield(record2, self.field2)))

    
class SetComparator(ValueComparator):
    """Compares fields which contain not a single string value but
    a set of string value (typically in the form of a delimited string).
    
    @ivar field1, field2: Each takes a record as a paremeter, and 
    returns a set of values representing the computed field. This
    may be achieved by splitting a single delimited column into values,
    or combining multiple columns.
    
    @ivar encode1, encode2: Functions applied to encode each value in the sets
    resulting from L{field1} and L{field2}, prior to comparing the sets.
    """
    
    def __call__(self, record1, record2):
        """Compare two records on a set-type field (either from
        splitting a single column, or combining multiple columns).
        
        @return: The average of the best comparison values for each
        string in the small set.
        """
        f1 = set(self.encode1(v1) for v1 in self.field1(record1))
        f2 = set(self.encode2(v2) for v2 in self.field2(record2))
        f1, f2 = sorted([f1, f2], key=len) # short sed, long set
        if len(f1) == 0 or len(f2) == 0:
            # Return the missing value result
            return self.comparevalues(None,None) 
        total = 0.0
        for v1 in f1:
            best = 0.0
            for v2 in f2:
                comp = self.comparevalues(v1,v2)
                best = max(best, comp)
            total += best # score of most similar item in the long set
        return total / len(f1)


class RecordComparator(OrderedDict):
    """Ordered dictionary mapping comparison weight fields to field comparison
    functions. The compare methods then compare pairs of records using those
    functions, returning namedtuple vectors corresponding to the
    results of each comparison function applied to the record.
    
    @ivar Weights: Namedtuple for the weight vector, with field names
    provided in the constructor.
    """
    
    def __init__(self, *comparators):
        """Parameteries with a variable number of (weight field, comparison
        function) pairs that will be applied to each pair of records."""
        super(RecordComparator, self).__init__(comparators)
        self.Weights = namedtuple("Weights", self.keys())

    def compare(self, recordA, recordB):
        """Compare two records and return a tuple of type Weights."""
        return self.Weights._make(
            comparator(recordA, recordB) for comparator in self.itervalues())
    
    def compare_all_pairs(self, records):
        """Compare all distinct pairs of records given a single in a list of records.

        @param records: List of record namedtuples.

        @return: Mapping pairs (record1, record2) to L{Weights} vector.
        """
        comparisons = {}
        for i in range(len(records)):
            for j in range(i):
                rec1, rec2 = records[i], records[j]
                assert rec1[0] != rec2[0]
                pair = tuple(sorted([rec1,rec2], key=lambda x:x[0]))
                if pair not in comparisons:
                    comparisons[pair] = self.compare(rec1, rec2)
        return comparisons
    
    def compare_indexed(self, indeces1, indeces2=None):
        """Perform indexed comparison.  Polymorphic to perform
        either a single-index comparison or a dual-index comparison."""
        if indeces2 is indeces1 or indeces2 is None:
            return self.compare_indexed_single(indeces1)
        else:
            return self.compare_indexed_dual(indeces1, indeces2)

    def compare_indexed_single(self, indeces):
        """Compare records against themselves, using indexing to reduce number
        of comparisons and caching to avoid comparing same two records twice.
        
        @return: Map from compared (record1,record2) to L{Weights} vector.
        """
        comparisons = {} # Map from (record1,record2) to L{Weights}
        for index in indeces.itervalues():
            for indexkey, records in index.iteritems():
                records = list(records)
                for i in range(len(records)):
                    for j in range(i):
                        pair = records[i], records[j]
                        if pair not in comparisons:
                            comparisons[pair] = self.compare(*pair)
        return comparisons

    def compare_indexed_dual(self, indeces1, indeces2):
        """Compare two sets of records using indexing to reduce number of comparisons.
        
        @param indeces1: List of L{Index} for first dataset.
        @param indeces2: List of corresponding L{Index} for second data set.
        @return: Map from (rec1,rec2) to comparison weights.
        """
        assert indeces1 is not indeces2 # Must be different!
        comparisons = {}
        for index1, index2 in zip(indeces1.itervalues(), indeces2.itervalues()):
            for indexkey in index1.iterkeys():
                if indexkey in index2:
                    for rec1 in index1[indexkey]:
                        for rec2 in index2[indexkey]:
                            pair = (rec1, rec2)
                            if pair not in comparisons:
                                comparisons[pair] = self.compare(*pair)
        return comparisons

    def write_comparisons(self, indeces1, indeces2, comparisons, stream):
        """Write pairs of compared records, together with index keys and 
        field comparison weights.  Inspection shows which index keys matched,
        and the field-by-field similarity.
        
        @param other: Indeces used on right-hand records (may be the same as self)
        @param recordcomparator: RecordComparator instance that produced L{comparisons},
        used to recreate the calculated non-encoded field values.
        @param comparisons: Map from (rec1,rec2) to weight vector.
        @param stream: Output stream to write the results to.
        """
        writer = csv.writer(stream)
        writer.writerow(indeces1.keys() + self.keys())
        field1 = [ comparator.field1 for comparator in self.itervalues() ]
        field2 = [ comparator.field2 for comparator in self.itervalues() ]
        for (rec1, rec2), weights in comparisons.iteritems():
            keys1 = [ idx.makekey(rec1) for idx in indeces1.itervalues() ]
            keys2 = [ idx.makekey(rec2) for idx in indeces2.itervalues() ]
            writer.writerow(keys1 + [ str(getfield(rec1,f)) for f in field1 ])
            writer.writerow(keys2 + [ str(getfield(rec2,f)) for f in field2 ])
            # Tuple of booleans indicating whether index keys are equal
            weightrow = [ int(k1 == k2) if (k1 is not None and k2 is not None) else ""
                             for k1,k2 in zip(keys1,keys2) ]
            weightrow += list(weights)
            writer.writerow(weightrow)

    @staticmethod
    def write_weights(idpairweights, fields, stream):
        """Take mapping from record pairs to comparison weights and writes it in CSV format
        @param idpairweights: Mapping (record1,record2) to L{Weights} vector
        @param fields: List of fields names in the comparison weights.
        @param ostream: Stream to which to write the CSV rows.
        """
        writer = csv.writer(stream)
        writer.writerow(("rec_id1", "rec_id2") + fields)
        for (rec1, rec2), comparison in sorted(idpairweights.iteritems()):
            writer.writerow((rec1[0],rec2[0]) + comparison)
