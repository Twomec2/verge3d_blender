"""
================================================================================
zipcruft.py - define default cruft file/folder/symlink name patterns.
See ziptools' ../_README.html for license, author, and other logistics.

This module is used by both zip-create.py and ziptools.py.  See the former
for more on cruft processing in general.

Defines default files, folders, and symlinks to be skipped for "-skipcruft" 
in the create script, and a default which can be imported and passed by other
clients to utilities in ziptools.  Edit as needed - either here, in the create
script, or in other direct-call clients.

These patterns are applied as case sensitive on all platforms, and will be 
matched by Python's fnmatch module against each item's base name (not an entire
pathname).  For pattern details. see fnmatch and ../_README.html; operators "*" 
(any characters), "?" (any single) and "[]" (any single bracketed) are supported.

Note: '.*' catches Mac '.DS_Store' Finder files, Mac '._*' Apple-double 
resource fork files on non-Mac filesystems, and any '.Trash*' recycle bins.  
Additional precoded patterns omit more-specific files.  Why must they junk-up 
our drives so?

[1.1] It may be useful to add '__pycache__' Python 3.X bytecode folders to 
cruft_skip too (they're remade on imports, just like .pyc and .pyo), but 
skipping here generates unique-item diffs in Mergeall; either skip or not 
skip in both, and Mergeall is frozen.  As is, '__pycache__' is kept, but its
bytecode contents is not.
================================================================================

"""

from fnmatch import fnmatchcase    # non-case-mapping version


#===============================================================================



# Cruft patterns: used by scripts, and callers that import it


# skip all files and folders matching these
cruft_skip = [
    '.*',                # Unix hidden files, Mac junk files
    '[dD]esktop.ini',    # Windows appearance
    'Thumbs.db',         # Windows caches
    '~*',                # Office temp files
    '$*',                # Windows recycle bin
    '*.py[co]'           # Python bytecode
    ]


# never skip any matching these, even if they match a skip pattern
cruft_keep = [
    '.htaccess'          # Apache website config files
    ]


# pass the pair as a dict to ziptools.createzipfile() if desired 
cruft_skip_keep = {'skip': cruft_skip,
                   'keep': cruft_keep}



#===============================================================================



def isCruft(filename, cruftpatts=cruft_skip_keep):
    """
    -----------------------------------------------------------------------
    Identify cruft by matching a file or folder basename "filename", to
    the patterns in dict "cruftpatts", using the fnmatch stdlib module.
    [1.1] Moved here from ziptools.py; this module encapsulates cruft.

    Returns True iff filename is a cruft item, which means it matches any
    pattern on "skip" list, and does not match any pattern on "keep" list,
    either of which can be empty to produce False results from any().
    No files are cruft if the entire patterns dict is empty (the default).
    See createzipfile() ahead for more on the "cruftpatts" dictionary.

    Note that this forces matches to be case sensitive on all platforms 
    for consistency.  By contrast, filename globs added in 1.1 are case 
    sensitive only on platforms that are too (which is also inconsistent,
    but cruft patterns seem likely to be focused on specific filenames).
    -----------------------------------------------------------------------
    """
    return (cruftpatts
            and
            any(fnmatchcase(filename, patt) for patt in cruftpatts['skip'])
            and not
            any(fnmatchcase(filename, patt) for patt in cruftpatts['keep']))

