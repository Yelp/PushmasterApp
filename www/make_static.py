#!/usr/bin/env python
import os
import sys

for line in sys.stdin:
    checksum, orig_path = line.rstrip().split('  ', 1)
    full_path = os.path.join('static', checksum, orig_path)
    
    full_dir = os.path.dirname(full_path) 
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)

    # copy
    file(full_path, 'w').write(file(orig_path).read())
