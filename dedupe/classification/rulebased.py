"""
Rule-based classification into match/non-match
==============================================

Uses a function of the similarity vector to determine match or non-match.  Note
that Nearest-Neighbour classifier allows an override rule to assist
classification.

.. moduleauthor:: Graham Poulter
"""

def classify_bool(rule, comparisons):
    """Use provided rule to classify similarity vectors as
    matches (True), non-matches (False) and uncertain (None).
    
    :type rule: function([:keyword:`float`,...]) :keyword:`bool` | :keyword:`None`
    :param rule: "is this similarity vector a match" - returns :keyword:`True`\
      :keyword:`False` or :keyword:`None`
    :type comparisons: {(`R`, `R`):[:class:`float`,...],...}
    :param comparisons: similarity vectors of compared record pairs.
    :rtype: {(`R`, `R`)...}, {(`R`, `R`)...}, {(`R`, `R`)...}
    :return: sets of matching, non-matching and uncertain record pairs
    """
    matches, nonmatches, uncertain = set(), set(), set()
    for pair, simvec in comparisons.iteritems():
        ismatch = rule(simvec)
        if ismatch is True:
            matches.add(pair)
        elif ismatch is False:
            nonmatches.add(pair)
        elif ismatch is None:
            uncertain.add(pair)
        else:
            raise ValueError("rulebased classify: %s is not True/False/None" % repr(ismatch))
    import logging
    logging.debug("rulebased classifier on %d vectors: %d matches, %d non-matches, %d uncertain", 
                  len(comparisons), len(matches), len(nonmatches), len(uncertain))
    return matches, nonmatches, uncertain

def classify(rule, comparisons):
    """Uses a rule to classify matches/non-matches using scores of 0.0 and 1.0,
    which is the format produced by :mod:`~classification.kmeans` and :mod:`~classification.nearest`.
    
    :type rule: function([:keyword:`float`,...]) :keyword:`bool` | :keyword:`None`
    :param rule: "is this similarity vector a match" - returns :keyword:`True`\
      :keyword:`False` or :keyword:`None`
    :rtype: {(`R`, `R`)::class:`float`}, {(`R`, `R`)::class:`float`}
    :return: classifier scores for match pairs (1.0) and non-match pairs (0.0)
    """
    match,nomatch,unknown = classify_bool(rule, comparisons)
    return dict((x,1.0) for x in match), dict((x,0.0) for x in nomatch)
