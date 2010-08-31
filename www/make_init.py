#!/usr/bin/env python
import os
import sys

print 'assets = {}'

for line in sys.stdin:
    checksum, orig_path = line.rstrip().split('  ', 1)
    full_path = os.path.join('static', checksum, orig_path)
    print 'assets[r"/%(orig_path)s"] = r"/%(full_path)s"' % locals()

print
