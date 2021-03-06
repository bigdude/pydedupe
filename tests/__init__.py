#!/usr/bin/env python

import logging
import os
import re
import sys
import unittest


def suite():
    """Generate a test suite from the test_* modules in this directory."""
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(tests_dir))
    testmods = ['tests.' + re.match(r'(.+?)\.py$', f).group(1)
                 for f in os.listdir(tests_dir)
                 if re.match(r'test_(.+?)\.py$', f) is not None]
    print "Testing Modules: ", ", ".join(testmods)
    return unittest.defaultTestLoader.loadTestsFromNames(testmods)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt='%Y-%m-%dT%H:%M:%S',
        format='%(asctime)s %(levelname)s - %(name)s - %(message)s')
    unittest.TextTestRunner(verbosity=2).run(suite())
