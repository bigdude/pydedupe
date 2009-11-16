"""
:mod:`encoding` -- Transformation and encoding of values.
=========================================================

.. moduleauthor:: Graham Poulter
"""

import re
"""Regular expression library"""

import dmetaphone
"""Phonetic text encoding with double metaphone"""

from functools import partial
"""Partial function application to configure encoders"""

def normspace(text):
    """Strip multiple and trailing spaces.
    
    >>> normspace(' a  b  ')
    u'a b'
    """
    return re.sub(ur"\s+", u" ", text.strip())

def nospace(text):
    """Strip all whitespace.
    
    >>> nospace(" a  b  ")
    u'ab'
    """
    return re.sub(ur"\s+", u"", text.strip())

def lowstrip(text):
    """Lowcase and strip extra space.
    
    >>> lowstrip(" A  b  ")
    u'a b'
    """
    return normspace(text.lower())

def digits(text):
    """Strip all except digits (for phone numbers).
    
    >>> digits("+27 (21) 1234567")
    '27211234567'
    """
    return re.sub(ur"\D+", "", text.strip())

def sorted_words(text):
    """Sort words.
    
    >>> sorted_words('c a b')
    'a b c'
    """
    return ' '.join(sorted(text.split(' ')))

def reverse(text):
    """Reverse text.
    
    >>> reverse('abc')
    'cba'
    """
    return text[::-1]

def urldomain(text):
    """Obtain the domain from the text of a URL.
    
    >>> urldomain("http://www.google.com")
    'google.com'
    >>> urldomain("www.google.com")
    'google.com'
    >>> urldomain("http://google.com")
    'google.com'
    >>> urldomain("http://www.google.com/a")
    'google.com'
    >>> urldomain("http://www.google.com/a/b")
    'google.com'
    """
    match = re.match(ur'(?:http://)?(?:www\.)?([^/]+)(?:/.*)?', text)
    if match is None: return text
    return match.group(1)

def emaildomain(text):
    """Obtain the domain from the text of an email address.
    
    >>> emaildomain("srtar@arst.com")
    'arst.com'
    >>> emaildomain("abc")
    'abc'
    """
    match = re.match(ur'([^@]+)@(.+)', text)
    if match is None: return text
    return match.group(2)

def wrap(*funcs):
    """Create a composited function from a list of unitary functions.
    For example, wrap(f1, f2, f3)(text) == f1(f2(f3(text)))
    
    >>> wrap(sorted_words, reverse)("world hello")
    'dlrow olleh'
    """
    def _wrapper(text):
        # Innermost function gets applies first
        for func in funcs[::-1]:
            text = func(text)
        return text
    return _wrapper



