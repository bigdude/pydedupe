"""K-means clustering of similarity vectors into two groups (matches and
non-matches).

The default kmeans implementation has the advantage in that it is
able to handle missing (None) values in the similarity vectors.  It does
this by "not counting" whenever it comes across None, which should produce
better results than replacing None with 0 in instances where two field
values could not be compared.

@author: Graham Poulter
@copyright: MIH Holdings
@license: GPL
"""

def kmeans_febrl(comparisons, distance, maxiter=50, sample=100.0):
    """Classify each pair of comparisons as match or nonmatch, by clustering
    weight vectors around "match centroind" and "nonmatch centroid"
       
    @param comparisons: mapping (rec1,rec2):weights from record pair to
    field-by-field comparison vector.
    
    @param distance: Function distance(v1,v2) of two similarity vectors
    returninng the floating point distance between them, discarding components
    having a None value.
    
    @return: set of matched pairs of records, set of non-matched pairs of records.
    """
    from dedupe.febrl.classification import KMeans
    # Return empty sets if there is nothing to classify
    if not comparisons: return set(), set()
    # Configure the FEBRL classifier
    kmeans = KMeans(dist_measure = distance,  
                    max_iter_count = maxiter,
                    centroid_init = "min/max", 
                    sample = sample)
    kmeans.train(comparisons, None, None) # Identify the centroids
    [match, nomatch, probablematch] = kmeans.classify(comparisons)
    return match, nomatch

def kmeans(comparisons, distance, maxiter=10, sample=None):
    """Classify each pair of comparisons as match or nonmatch, by clustering
    weight vectors around "match centroind" and "nonmatch centroid". 
    
    The match/nonmatch centroids are initialised using the largest/smallest
    occuring value for each component.
       
    @param comparisons: mapping (rec1,rec2):weights from record pair to
    field-by-field comparison vector.
    
    @param distance: Function distance(v1,v2) of two similarity vectors
    returninng the floating point distance between them, discarding components
    having a None value.
    
    @return: set of matched pairs of records, set of non-matched pairs of
    records.
    """
    # Get length of the comparison vector
    k,v = comparisons.popitem()
    vlen = len(v)
    vidx = range(vlen)
    comparisons[k] = v
    
    # Mapping from key to (value, initial class assignment), where
    # all items are initially false, for non-match class.
    assignments = dict( (k,[v,False]) for k,v in comparisons.iteritems() )
    
    # Get initial centroids
    high_centroid = [ max(x[i] for x in comparisons.itervalues() 
                          if x[i] is not None) for i in vidx ]
    low_centroid = [ min(x[i] for x in comparisons.itervalues() 
                         if x[i] is not None) for i in vidx ]
    
    # Number of items that changed class
    n_changed = 1
    # Number of classifier iterations
    iters = 0

    while n_changed >= 0 and iters < maxiter:
        n_changed = 0
        iters += 1
        
        # Sums for the values in the high/low classes
        high_total = [0.0] * vlen
        low_total = [0.0] * vlen
        # Number of non-None values in each component for high/low class
        high_count = [0] * vlen
        low_count = [0] * vlen
    
        # Now assign the vectors to centroids
        for k, (v,match) in assignments.iteritems():
            dist_high = distance(v, high_centroid)
            dist_low = distance(v, low_centroid)
            if dist_high < dist_low:
                if not match: 
                    n_changed += 1	
                assignments[k][1] = True # Set match to True
                for i in vidx:
                    if v[i] is not None:
                        high_total[i] += v[i]
                        high_count[i] += 1 
            else:
                if match: 
                    n_changed += 1
                assignments[k][1] = False # Set match to False
                for i in vidx:
                    if v[i] is not None:
                        low_total[i] += v[i]
                        low_count[i] += 1
                        
        high_centroid = [ high_total[i]/high_count[i] for i in vidx ]
        low_centroid = [ low_total[i]/low_count[i] for i in vidx ]
        
    matches = set(k for k, (v,match) in assignments.iteritems() if match)
    nomatches = set(k for k, (v,match) in assignments.iteritems() if not match)
    return matches, nomatches
