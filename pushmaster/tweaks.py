import sys

# Hack for python 2.6. This is required because otherwise the logging module
# will try to import the multiprocessing module, which tries to load a C module
# ("_multiprocessing"), which causes appengine to freak out.
if sys.version_info[:2] >= (2, 6):
    import logging
    logging.logMultiprocessing = False
