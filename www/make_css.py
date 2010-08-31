#!/usr/bin/env python
import os
import re
import sys

import images_assets

url_re = re.compile(r'url\(([^)]+)\)')
css_content = sys.stdin.read()
css_sub_content = url_re.sub(lambda m: 'url("%s")' % images_assets.assets[m.group(1)], css_content)
sys.stdout.write(css_sub_content)
sys.stdout.flush()
