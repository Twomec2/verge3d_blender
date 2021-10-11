"""
=================================================================================
zipsymlinks.py - implementation of symlinks for the ziptools package.
See ziptools' ../_README.html for license, author, and other logistics.

Moved here because this is fairly gross code - and should not
be required of clients of Python's zipfile module: fix, please!

ziptools zips and unzips symlinks portably on Windows and Unix, subject
to the constraints of each platform and Python's libraries (see section
"PYTHON SYMLINKS SUPPORT" in ziptools.py for a summary).  Symlinks path
separators are not portable between Windows and Unix, but link path are
auto-adjusted here for the hosting platform's syntax unless "nofixlinks".

See ./ziptools.py's main docstring for more symlinks documentation.

Recent upgrades:
  [1.1] Set per-link permissions in the zip file on creates (not a constant).
  [1.1] Handle empty folder names on extracts (produced by "." targets).
For the next 2: use forged links on creates and dummy stub files on extracts:
  [1.1] Don't die on Windows in Python 2.X, even though symlinks not supported.
  [1.1] Don't die on Android, even though symlinks not supported in general.
The following were 1.2 fixes for trivial 1.1 misses:
  [1.2] 'trace' is now passed from ziptools.py, since this now prints things.
  [1.2] also lstrip() os.altsep to drop any '/' on Windows (along with '\').
  [1.2] catch decoding errors for link-path bytes fetched from zipfiles.

Caveats:
  - symlinks are not supported on Windows in Python 2.X (3.2- is marginal).
  - Windows requires admin permission to write symlinks (use right-clicks).
  - Windows supports symlinks only on NTFS filesystem drives (not exFAT/FAT).
  - symlinks are not present in Windows until Vista (XP is right out).
  - Android emulated filesystems fail on symlink permission errors (ignored). 
  - Encoding of link paths in zipfiles is unclear (write/assume UTF-8 bytes).
=================================================================================
"""

from __future__ import print_function    # python2.X compatibility
import os, sys, time
import zipfile as zipfilemodule          # versus the passed zipfile object

# UTC timestamp zip [1.2]
from .zipmodtimeutc import addModtimeUTC

# portability exceptions
RunningOnWindows = sys.platform.startswith('win')



#===============================================================================


"""
ABOUT THE "MAGIC" BITMASK

Magic = type + permission + DOS is-dir flag?
    >>> code = 0xA1ED0000
    >>> code
    2716663808
    >>> bin(code)
    '0b10100001111011010000000000000000'

Type = symlink (0o12/0xA=symlink 0o10/0x8=file, 0o04/0x4=dir) [=stat() bits]
    >>> bin(code & 0xF0000000)
    '0b10100000000000000000000000000000'
    >>> bin(code >> 28)
    '0b1010'
    >>> hex(code >> 28)
    '0xa'
    >>> oct(code >> 28)
    '0o12'

Permission = 0o755 [rwx + r-x + r-x]
    >>> bin((code & 0b00000001111111110000000000000000) >> 16)
    '0b111101101'
    >>> bin((code >> 16) & 0o777)
    '0b111101101'

DOS (Windows) is-dir bit
    >>> code |= 0x10 
    >>> bin(code)
    '0b10100001111011010000000000010000'
    >>> code & 0x10
    16
    >>> code = 0xA1ED0000
    >>> code & 0x10
    0

Full format:
    TTTTsstrwxrwxrwx0000000000ADVSHR
    ^^^^____________________________ file type, per sys/stat.h (BSD)
        ^^^_________________________ setuid, setgid, sticky
           ^^^^^^^^^________________ permissions, per unix style
                    ^^^^^^^^________ Unused (apparently)
                            ^^^^^^^^ DOS attribute bits: bit 0x10 = is-dir

Discussion:
    http://unix.stackexchange.com/questions/14705/
        the-zip-formats-external-file-attribute
    http://stackoverflow.com/questions/434641/  
        how-do-i-set-permissions-attributes-
        on-a-file-in-a-zip-file-using-pythons-zip/6297838#6297838
"""


SYMLINK_TYPE  = 0xA
SYMLINK_PERM  = 0o755    # no longer used
SYMLINK_ISDIR = 0x10
SYMLINK_MAGIC = (SYMLINK_TYPE << 28) | (SYMLINK_PERM << 16)

assert SYMLINK_MAGIC == 0xA1ED0000, 'Bit math is askew'    


# [1.1] ziptools now saves permission bits from the link itself instead of 
# always using 0o755, because 1.1 "-permissions" extracts now propagate all
# permissions.  Custom link permissions may be rare, but are supported here
# on platforms that support them too (Windows doesn't, in Python's builtins).
# Nit: could just set this to type alone, but retaining the coding history.

SYMLINK_MAGIC &= 0b11111110000000001111111111111111   # mask off permission bits



#===============================================================================



def addSymlink(filepath, zippath, zipfile, trace=print):
    """
    ----------------------------------------------------------------------------
    Create (zip): add a symlink (to a file or dir) to the archive.

    'filepath' is the (possibly-prefixed and absolute) path to the link file.
    'zippath'  is the (relative or absolute) path to record in the zip itself.
    'zipfile'  is the ZipFile object used to format the created zip file. 
    'trace'    is the print function sent to the ziptools.py top-level [1.2].

    This adds the symlink itself, not the file or directory it refers to, and
    uses low-level tools to add its link-path string.  Python's zipfile module
    does not support symlinks directly: see https://bugs.python.org/issue18595.
    Use atlinks=True in ziptools.py caller to instead add items links reference.

    Windows requires administrator permission and NTFS to create symlinks, 
    and a special argument to denote directory links if dirs don't exist: the
    dir-link bit set here is used by extracts to know to pass the argument.
 
    Coding notes:
    1) The ZipInfo constructor sets create_system and compress_type (plus a
       few others), so their assignment code here is not required but harmless.

    2) os.path.normpath() can change meaning of a path that with symlinks, but
       it is used here on the path of the link itself, not the link-path text.

    3) In ziptools, 'filepath' always has a '\\?\' long-pathname prefix on Windows
       (only), due to the just-in-case requirements of os.walk() in the caller;
       'zippath' is just 'filepath' without the special prefix.  os.path.splitdrive()
       drops both '\\?\' and 'C:'; os.path.normpath() does nothing with \\?\ paths.

    4) [1.2] As passed to this, 'zippath' has already been transformed for the
       '-zip@/zipat' option, if it is being used for this zip; send it along.
       When used, 'zippath' may now be arbitrarily different from 'filepath'.

    5) Python 2.X on Windows should never get here: it cannot detect symlinks
       (os.path.islink() returns False for symlinks); coded to handle anyhow.
    ----------------------------------------------------------------------------
    """

    assert os.path.islink(filepath)
    if hasattr(os, 'readlink'):
        try:
            linkpath = os.readlink(filepath)        # str of link itself
        except:
            trace('--Symlink not supported')        # any other issues [1.1]
            linkpath = 'symlink-not-supported'      # forge a link-to path 
    else:
        trace('--Symlink not supported')            # python2.X on Windows? [1.1]
        linkpath = 'symlink-not-supported'          # forge a link-to path 
    
    # 0 is windows, 3 is unix (e.g., mac, linux) [and 1 is Amiga!]
    createsystem = 0 if RunningOnWindows else 3 

    # else time defaults in zipfile to Jan 1, 1980
    linkstat = os.lstat(filepath)                   # stat of link itself
    origtime = linkstat.st_mtime                    # mtime of link itself
    ziptime  = time.localtime(origtime)[0:6]        # first 6 tuple items

    # zip mandates '/' separators in the zipfile
    allseps = os.sep + (os.altsep or '')            # +leading '/' on win [1.2]
    if not zippath:                                 # pass None to equate
        zippath = filepath
    zippath = os.path.splitdrive(zippath)[1]        # drop Windows drive, unc
    zippath = os.path.normpath(zippath)             # drop '.', double slash...
    zippath = zippath.lstrip(allseps)               # drop leading slash(es)
    zippath = zippath.replace(os.sep, '/')          # no-op if unix or simple
   
    newinfo = zipfilemodule.ZipInfo()               # new zip entry's info
    newinfo.filename      = zippath
    newinfo.date_time     = ziptime
    newinfo.create_system = createsystem            # woefully undocumented
    newinfo.compress_type = zipfile.compression     # use the file's default
    newinfo.external_attr = SYMLINK_MAGIC           # type plus dflt permissions

    if os.path.isdir(filepath):                     # symlink to dir?
        newinfo.external_attr |= SYMLINK_ISDIR      # DOS directory-link flag

    # [1.1] set this link's permission bits
    linkperms = (linkstat[0] & 0xFFFF) << 16        # zero-filled, both ends
    newinfo.external_attr |= linkperms              # set bits from file 

    zipfile.writestr(newinfo, linkpath)             # add to the new zipfile

    # record link's UTC timestamp [1.2]
    addModtimeUTC(zipfile, utcmodtime=origtime)     # to be written on zip close()



#===============================================================================



def isSymlink(zipinfo):
    """
    ----------------------------------------------------------------------------
    Extract: check the entry's type bits for symlink code.
    This is the upper 4 bits, and matches os.stat() codes.
    ----------------------------------------------------------------------------
    """
    return (zipinfo.external_attr >> 28) == SYMLINK_TYPE



def symlinkStubFile(destpath, linkpath, trace):
    """
    ----------------------------------------------------------------------------
    Extract: simulate an unsupported symlink with a dummy file [1.1].
    The is subpar, but it's better than killing the rest of the unzip.
    No stub is made for symlink filenames with non-portable characters.
    Must encode, else non-ASCII Unicode bombs on py2.X for 'w' text 
    files, and Unicode text-file interfaces differ in py2.X and 3.X.
    ----------------------------------------------------------------------------
    """
    try:
        linkpath = linkpath.encode('utf8')    # finesse 3.X/2.X unicode diffs [1.2]
        bogus = open(destpath, 'wb')          # record linkpath in plain text file
        bogus.write(linkpath)                 # though linkpath forged in Win+2.X
        bogus.close()
    except:
        # may fail for illegal filename characters, access perms, etc.
        trace('--Could not make stub file for', destpath)



#===============================================================================



def extractSymlink(zipinfo, pathto, zipfile, nofixlinks=False, trace=print):
    """
    ----------------------------------------------------------------------------
    Extract (unzip): read the link path string, and make a new symlink.

    'zipinfo' is the link file's ZipInfo object stored in zipfile.
    'pathto'  is the extract's destination folder (relative or absolute)
    'zipfile' is the ZipFile object, which reads and parses the zip file.
    'trace'   is the print function sent to the ziptools.py top-level [1.2].
    'nofixlinks' is described ahead.
    
    On Windows, this requires admin permission and an NTFS destination drive.
    On Unix, this generally works with any writable drive and normal permission.
    
    Uses target_is_directory on Windows if flagged as dir in zip bits: it's not
    impossible that the extract may reach a dir link before its dir target.

    Adjusts link path text for host's separators to make links portable across
    Windows and Unix, unless 'nofixlinks' (which is command arg -nofixlinks).
    This is switchable because it assumes the target is a drive to be used
    on this platform - more likely here than for mergeall external drives.

    In ziptools, pathto already has a '\\?\' long-path prefix on Windows (only);
    this ensures that the file calls here work regardless of joined-path length.

    Caveat: some of this code is redundant with ZipFile._extract_member() in
    zipfile, but that library does not expose it for reuse here.  Some of this 
    is also superfluous if we only unzip what we zip (e.g., Windows drive names 
    won't be present and upper dirs will have been created), but that's not 
    ensured for all zips created in the wild that we may process here.

    Limitation: unlike the general ZipFile.extract(), this does not "sanitize" 
    (i.e., mangle) non-portable filename characters on Windows to "_" (see 
    ZipFile._sanitize_windows_name()).  This is partly because zipfile marks 
    this as a private API; partly because the odds of extracting a symlink  
    with illegal characters on Windows seem near zero; and partly because this 
    is a broader problem that may be best relegated to interoperability caveat - 
    legal characters may vary per platform and filesystem.  As coded, a symlink 
    with characters illegal on any unzip platform generates an error message 
    without a stub file, but does not terminate the extract for other items.
    
    TBD:
    1) Should this also call os.chmod() with the zipinfo's permission bits?

       [1.1] ziptools now _does_ do this on request, though this happens in 
       the caller (not here).  This is closed.

    2) Does the UTF-8 decoding of the linkpath bytes suffice in all contexts?
       zipfile's 3.X writestr() encodes str data to UTF-8 bytes before writes,
       but other zippers may differ (and it seems impossible to know how).

       [1.2] This now catches decoding errors, and forges a link so extract
       continues.  It could stay with bytes instead, but their encoding may 
       not meet the underlying platform's os.symlink() expectation (yes, blah).

    3) Is the "sanitize" policy above reasonable?  No use cases have been seen,
       so it's impossible to judge the issue's scope; please report problems.

    4) As coded, symlink permissions errors on Windows due to non-admin runs
       generate a stub file and continue; should this throw an error instead?
    ----------------------------------------------------------------------------
    """

    assert zipinfo.external_attr >> 28 == SYMLINK_TYPE
    
    zippath  = zipinfo.filename                         # pathname in the zip 
    linkpath = zipfile.read(zippath)                    # original link path str
    try:
        linkpath = linkpath.decode('utf8')              # must match types ahead
    except UnicodeDecodeError:                          # don't die if !utf8 [1.2]
        trace('--Symlink not decodable')
        linkpath = u'symlink-not-decodable'             # ensure unicode in 2.X

    # undo zip-mandated '/' separators on Windows
    zippath  = zippath.replace('/', os.sep)             # no-op if unix or simple

    # drop Win drive + unc, leading slashes, '.' and '..'
    zippath  = os.path.splitdrive(zippath)[1]
    zippath  = zippath.lstrip(os.sep)                   # if other program's zip
    allparts = zippath.split(os.sep)
    okparts  = [p for p in allparts if p not in ('.', '..')]
    zippath  = os.sep.join(okparts)

    # where to store link now (assume chars portable)
    destpath = os.path.join(pathto, zippath)            # hosting machine path
    destpath = os.path.normpath(destpath)               # perhaps moot, but...

    # make leading dirs if needed
    upperdirs = os.path.dirname(destpath)               # skip if './link' => '' [1.1]
    if upperdirs and not os.path.exists(upperdirs):     # will fail if '' or exists;
        os.makedirs(upperdirs)                          # exists_ok in py 3.2+ only

    # adjust link separators for the local platform
    if not nofixlinks:
        linkpath = linkpath.replace(u'/', os.sep).replace(u'\\', os.sep)

    # test+remove link, not target
    if os.path.lexists(destpath):                       # else symlink() fails
        os.remove(destpath)

    # windows dir-link arg
    isdir = zipinfo.external_attr & SYMLINK_ISDIR
    if (isdir and                                       # not suported in py 2.X
        RunningOnWindows and                            # ignored on unix in 3.3+
        int(sys.version[0]) >= 3):                      # never required on unix 
        dirarg = dict(target_is_directory=True)
    else:
        dirarg ={}

    # make the link in dest
    if hasattr(os, 'symlink'):
        try:
            os.symlink(linkpath, destpath, **dirarg)    # store new link in dest
        except:
            # including non-admin Windows
            trace('--Symlink not supported')            # any python on Android [1.1]
            symlinkStubFile(destpath, linkpath, trace)  # make dummy file?, go on
    else:
        trace('--Symlink not supported')                # python2.X on Windows [1.1]
        symlinkStubFile(destpath, linkpath, trace)      # make dummy file, go on

    return destpath                                     # savepath as made here

    # and caller sets link's modtime and permissions where supported
