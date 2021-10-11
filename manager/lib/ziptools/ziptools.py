#!/usr/bin/python
"""
================================================================================
ziptools.py - the main library module of the ziptools system.
See ziptools' ../_README.html for license, author, and other logistics.

Tools to create and extract zipfiles containing a set of files, folders, and
symbolic links.  All functions here are callable, but the main top-level entry
points are these two (see ahead for more on their arguments):

   createzipfile(zipname, [addnames],
         storedirs=True, cruftpatts={}, atlinks=False, trace=print, zipat=None)
                     
   extractzipfile(zipname, pathto='.',
         nofixlinks=False, trace=print, permissions=False)

Pass "trace=lambda *p, **k: None" to silence most messages from these calls.
See also scripts zip-create.py and zip-extract.py for command-line clients,
and zipcruft.cruft_skip_keep for a default "cruftpatts" cruft-file definition. 
All of these have additional documentation omitted here.

This ziptools package mostly extends Python's zipfile module with top-level
convenience tools that add some important missing features:

   * For folders, adds the folder's entire tree to the zipfile automatically
   * For zipfile creates, filters out cruft (hidden metadata) files on request
   * For zipfile extracts, retains original modtimes for files, folders, links
   * For symlinks, adds/recreates the link itself to/from zipfiles, by default
   * For Windows, supports long pathnames by lifting the normal length limit
   * For zipfile extracts, optionally retains access permissions for all items
   * For all items, adds UTC-timestamp modtimes immune to DST and timezone

Docs which span creates and extracts (see these functions for more):

CRUFT HANDLING:
   This script sidesteps other tools' issues with ".*" cruft files (metadata that
   is normally hidden): by default, they are not silently/implicitly omitted in
   zips here for completeness, but can be omitted by passing a filename-patterns
   definition structure to the optional "cruftpatts" argument.

   See zipcruft.py for pattern defaults to import and pass, and zipfile-create.py
   for more background.  Most end-user zips should skip cruft files (see Mergeall:
   cruft can be a major issue on Mac OS in data to be transferred elsewhere).

WINDOWS LONG PATHS:
   This program, like Mergeall, supports pathnames that are not restricted to the
   usual 260/248-character length limit on all versions of Windows.  To lift the
   limit, pathnames are automatically prefixed with '\\?\' as needed, both when
   adding to and extracting from archives.  This allows archives created on
   platforms without such limits to be unzipped and rezipped on Windows machines.

   The \\?\-prefix magic is internal, and hidden from the user as much as possible.
   It also makes paths absolute, but relative paths are still fully supported:
   absolute paths are not propagated to the archive when creating, and impact
   only output messages on Windows when extracting (where we strip the prefix
   and try to map back to relative as needed to keep the messages coherent).

SYMLINKS SUPPORT:
   This package also supports adding symlinks (symbolic links) to and extracting
   them from zip archives, on both Unix and Windows with Python 3.X, but only on
   Unix with Python 2.X.  Windows requires admin permissions and NTFS filesystem
   destinations to create symlinks from a zip file; Unix does not.

   The underlying Python zipfile module doesn't support symlinks directly today,
   short of employing the very low-level magic used in ziptools_symlinks.py here,
   and there is an open bug report to improve this:

      https://bugs.python.org/issue18595
      https://mail.python.org/pipermail/python-list/2005-June/322179.html
      https://duckduckgo.com/?q=python+zipfile+symlink

   Symlinks customize messages with "~" characters in creation and "(Link)"
   prefixes in extraction, because they are a special-enough case to call out in
   logs, and may require special permission and handling to unzip and use on
   Windows.  For example, link creation and extraction messages are as follows:

      Adding  link  ~folder test1/dirlink   # create message
      (Link) Extracted test1/dirlink        # extract message

   By default, zipfile creation zips links themselves verbatim, not the items they
   refer to.  Pass True to the "atlinks" function argument to instead follow links
   and zip the items they refer to.  Unzipping restores whatever was zipped.

   When links are copied verbatim, extracts adjust the text of a link's path to
   use the hosting platform's separators - '\' for Windows and '/ for Unix.  This
   provides some degree of link portability between Unix and Windows, but is
   switchable with "nofixlinks" because it may not be desirable in all contexts
   (e.g., when unzipping to a drive to be used elsewhere).  Symlinks will still
   be nonportable if they contain other platform-specific syntax, such as Windows
   drive letters or UNC paths, or use absolute references to extra-archive items.

   When "atlinks" is used to follow links and copy items they refer to, recursive
   links are detected on platforms and Pythons that support stat objects' st_ino
   (a.k.a. inode) unique directory identifiers.  This includes all Unix contexts,
   and Windows as of Python 3.2 (other contexts fails on path or memory errors).
   Recursive links are copied themselves, verbatim, to avoid loops and errors.

   Besides symlinks, FIFOs and other exotic items are always skipped and ignored;
   items with system state can't be transferred in a zipfile (or Mergeall mirror).
   See also the top-level README for more on symlinks.  Due to known limitations,
   symlinks on Windows function correctly but do not retain original modtimes.

PYTHON SYMLINKS SUPPORT:
   The following table summarizes Python's current symlink support, which wholly
   determines that of ziptools.  In it, IO means basic os.{readlink, symlink} 
   read/write calls, lchmod is the os module's permissions writer, and S_F_S 
   stands for the os.supports_follow_symlinks registration table of tools that 
   can work on symlinks instead of their referents.  utime is required for 
   modtimes, and chmod or lchmod for permissions, and there is no lutime:

      Platform   Python   IO    lchmod   S_F_S   S_F_S content
      Windows    2.X      no    no       no      n/a
      Windows    3.X      yes   no       yes     os.stat only
      Unix       2.X      yes   yes      no      n/a
      Unix       3.X      yes   yes      yes     os.{utime, chmod,...}

   Per this table, Unix gets the best coverage, though its 2.X cannot propagate 
   symlink modtimes because it has no symlink utime, and must use lchmod instead
   of chmod.  Windows support is spottier: 2.X has none, and 3.X cannot update
   modtimes or permissions.  Worse, os.path.islink() simply returns False for 
   symlinks on Windows+Python 2.X, which means symlinks cannot be detected, and
   are followed on zips (creates); use 3.X if you care.  Nits: Python 3.X has S_F_S 
   only in 3.3 and later, and all of this is may change (and hopefully will...).

PERMISSIONS SUPPORT:
   As of ziptools version [1.1], extracts (unzips) now propagate Unix permissions
   for files, folders, and symlinks.  Due to interoperability concerns, however, 
   this option only works if it is explicitly selected, and should generally be 
   used only for Unix from+to.  See the extract function below for more details.

FAILURES POLICY:
   Per the user guide, ziptools' general policy is to report but ignore failures
   of permissions, modtimes, and symlinks (because they are metadata), but end
   the run for failures of files and folders (because they are core data).
================================================================================
"""


from __future__ import print_function         # py 2.X compatibility

import os, sys, shutil
from zipfile import ZipFile, ZIP_DEFLATED     # stdlib base support

# nested package so same if used as main script or package in py3.X

# default cruft-file patterns, import here for importers ({}=don't skip)
from .zipcruft import cruft_skip_keep, isCruft    # [1.1] isCruft moved

# major workaround to support links: split this narly code off to a module...
from .zipsymlinks import addSymlink, isSymlink, extractSymlink

# also major: fix any too-long Windows paths on archive adds and extracts
from .ziplongpaths import FWP, UFWP

# UTC timestamp zip/unzip [1.2]
from .zipmodtimeutc import addModtimeUTC, getModtimeUTCorLocal

# interoperability nits [1.1]
RunningOnPython2 = sys.version.startswith('2')
RunningOnMacOS   = sys.platform.startswith('darwin')
RunningOnWindows = sys.platform.startswith('win')



#===============================================================================



_builtinprint = print

def print(*pargs, **kargs):
    r"""
    -----------------------------------------------------------------------
    [1.1] Avoid print() exceptions on Python 2.X and Windows.  This code
    redefines print for the rest of this module only, but the custom print 
    becomes the default for "trace" arguments here; you can import this and
    pass it back in, but shouldn't need to ("trace" is mostly for silencing).
    This code addresses two potentials for aborts (print() exceptions):

    1) On Python 2.X, prints of non-ASCII Unicode to a pipe on Unix can 
    throw a to-ASCII encoding exception, even though the same print to the 
    console works fine.  Work around by manually encoding unicode arguments 
    to UTF-8 when printed.  This was escalated by forcing unicode filenames 
    for zip interoperability, but the exceptions also happened if 2.X 
    unzipped a 3.X zip and received decoded unicode for non-ASCII names.

    2) On Windows, printing Unicode is perilous in general.  The user may 
    have set PYTHONIOENCODING to UTF-8, but this is too much to require;
    the Windows default CP437 cannot be assumed because it may not apply
    on the host; and printing unsupported characters triggers an encoding
    exception in any case.  To avoid exceptions, replace all non-ASCII 
    characters for message display only, and specialize for 3.X / 2.X str
    (e.g., 'Li[\u241][\u241]ux.png' / 'Li[\xC3][\xB1][\xC3][\xB1]ux.png').
    This could use ascii() in 3.X (only), but opted to match 2.X displays.
    mungestr2X doesn't work on 3.X bytes, but this doesn't have to care.

    [1.2] This is now also imported and used by interactive-mode prints in 
    main scripts, to avoid similar (though unlikely) non-ASCII print aborts.
    This applies only to prints on Windows in this context: input() text 
    is a str in 2.X, and so need not be down-converted from unicode.
    Creating the abort required pasting a Unicode filename into scripts.
    -----------------------------------------------------------------------
    """
    usersetting = os.environ.get('PYTHONIOENCODING')  # not currently used 

    # 3.X str: decoded codepoints
    mungestr3X = \
        lambda s: u''.join(c if ord(c) <= 127 else ('[\\u%d]' % ord(c)) for c in s)

    # 2.X str: encoded bytes
    mungestr2X = \
        lambda s: b''.join(c if ord(c) <= 127 else ('[\\x%X]' % ord(c)) for c in s)

    if RunningOnPython2:
        pargs = [parg.encode('UTF-8') if type(parg) is unicode else parg
                      for parg in pargs]
        if RunningOnWindows:
            pargs = [mungestr2X(parg) if type(parg) is str else parg
                          for parg in pargs]

    elif RunningOnWindows:
        pargs = [mungestr3X(parg) if type(parg) is str else parg
                      for parg in pargs]
        
    try:
        _builtinprint(*pargs, **kargs)
    except UnicodeEncodeError:
        print('--Cannot print filename: message skipped')    # we tried; punt!



#===============================================================================


 
def tryrmtree(folder, trace=print):
    """
    -----------------------------------------------------------------------
    Utility: remove a folder by pathname if needed before unzipping to it.
    Optionally run by zip-extract.py in interactive mode, but not by the
    base extractzipfile() function here: manually clean targets as needed.

    Python's shutil.rmtree() can sometimes fail on Windows with a "directory
    not empty" error, even though the dir _is_ empty when inspected after
    the error, and running again usually fixes the problem (deletes the
    folder successfully).  Bizarre, yes?  See the rmtreeworkaround() onerror
    handler in Mergeall's backup.py for explanations and fixes.  rmtree()
    can also fail on read-only files, but this is likely intended by users.
    -----------------------------------------------------------------------
    """

    if os.path.exists(FWP(folder)):
        trace('Removing', folder)
        try:
            if os.path.islink(FWP(folder)):
                os.remove(FWP(folder))
            else:
                shutil.rmtree(FWP(folder, force=True))    # recurs: always \\?\
        except Exception as why:
            print('shutil.rmtree (or os.remove) failed:', why)
            input('Try running again, and press Enter to exit.')
            sys.exit(1)



#===============================================================================



def isRecursiveLink(dirpath):
    """
    -----------------------------------------------------------------------
    Use inodes to identify each part of path leading to a link,
    on platforms that support inodes.  All Unix/Posix do, though
    Windows Python doesn't until till 3.2 - if absent, allow
    other error to occur (there are not many more options here;
    on all Windows, os.path.realpath() is just os.path.abspath()).
    
    This is linearly slow in the length of paths to dir links,
    but links are exceedingly rare, "atlinks" use in ziptools
    may be rarer, and recursive links are arguably-invalid data.
    Recursion may be better than os.walk when path history is
    required, though this incurs overheads only if needed as is.
    
    dirpath does not have a \\?\ Windows long-path prefix here;
    FWP adds one and also calls abspath() redundantly - but only
    on Windows, and we need abspath() on other platforms too.
    -----------------------------------------------------------------------
    """
    trace = lambda *args: None                  # or print to watch

    # called iff atlinks: following links
    if (not os.path.islink(FWP(dirpath)) or     # dir item not a link?
        os.stat(os.getcwd()).st_ino == 0):      # platform has no inodes?
        return False                            # moot, or hope for best 
    else:
        # collect inode ids for each path extension except last
        inodes = []
        path = []
        parts = dirpath.split(os.sep)[:-1]      # all but link at end
        while parts:
            trace(path, parts)
            path    += [parts[0]]               # add next path part
            parts    = parts[1:]                # expand, fetch inode
            thisext  = os.sep.join(path)
            thispath = os.path.abspath(thisext)
            inodes.append(os.stat(FWP(thispath)).st_ino)

        # recursive if points to item with same inode as any item in path               
        linkpath = os.path.abspath(dirpath)
        trace(inodes, os.stat(FWP(linkpath)).st_ino)
        return os.stat(FWP(linkpath)).st_ino in inodes



def isRecursiveLink0(dirpath, visited):
    """
    -----------------------------------------------------------------------
    ABANDONED, UNUSED: realpath() cannot be used portably,
    because it is just abspath() on Windows Python (but why?).
    
    Trap recursive links to own parent dir, but allow multiple
    non-recursive link visits.  The logic here is as follows:
    If we've reached a link that leads to a path we've already
    reached from a link AND we formerly reached that path from
    a link located at a path that is a prefix of the new link's
    path, then the new link must be recursive.  No, really...
    Catches link at visit #2, but avoids overhead for non-links.
    -----------------------------------------------------------------------
    """
    # called iff atlinks: following links
    if not os.path.islink(dirpath):
        # skip non-links
        return False                                      # don't note path
    else:
        # check links history
        realpath = os.path.realpath(dirpath)              # dereference, abs
        #print('\t', dirpath, '\n\t', realpath, sep='')
        if (realpath in visited and
            any(dirpath.startswith(prior) for prior in visited[realpath])):
            return True          
        else:
            # record this link's visit
            visited[realpath] = visited.get(realpath, []) # add first or next
            visited[realpath].append(dirpath)
            return False



#===============================================================================



class CreateStats:
    """
    -----------------------------------------------------------------------
    Helper for recursive create (zip) stats counters [1.1].
    May also pass same mutable instance instead of using +=.
    -----------------------------------------------------------------------
    """
    attrs = 'files', 'folders', 'links', 'unknowns', 'crufts'

    def __init__(self):
        for attr in self.attrs:
            setattr(self, attr, 0)       # or exec() strs

    def __iadd__(self, other):           # += all attrs in place
        for attr in self.attrs:
            setattr(self, attr, getattr(self, attr) + getattr(other, attr))
        return self

    def __repr__(self, format='%s=%%d'):
        display = ', '.join(format % attr for attr in self.attrs)
        return display % tuple(getattr(self, attr) for attr in self.attrs) 



class ExtractStats(CreateStats):
    """
    Extract (unzip) stats: unknowns unlikely, no crufts or recursion.
    """
    attrs = 'files', 'folders', 'links', 'unknowns'



def _testCreateStats():
    x = CreateStats()
    print(x)  # files=0, folders=0, links=0, unknowns=0, crufts=0

    x.files += 1; x.folders += 2;  x.links += 3
    print(x)  # files=1, folders=2, links=3, unknowns=0, crufts=0

    y = CreateStats()
    y.folders += 10; y.unknowns += 20
    x += y
    print(x)  # files=1, folders=12, links=3, unknowns=20, crufts=0



#===============================================================================



def addEntireDir(thisdirpath,      # pathname of directory to add (rel or abs)
                 zipfile,          # open zipfile.Zipfile object to add to 
                 stats,            # counters instance, same at all levels [1.1]
                 thiszipatpath,    # modified pathname if zipat/zip@ used [1.2]
                 storedirs=True,   # record dirs explicitly in zipfile?
                 cruftpatts={},    # cruft files skip/keep, or {}=do not skip
                 atlinks=False,    # zip items referenced instead of links?
                 trace=print):     # trace message router (or lambda *x: None)
    """
    -----------------------------------------------------------------------
    Add the full folder at thisdirpath to zipfile by adding all its parts.
    Python's zipfile module has extractall(), but nothing like an addall()
    (apart from simple command-line use).  The top-level createzipfile() 
    kicks off the recursion here, and docs more of this function's utility.

    ADDING DIRS: 
       Dirs (a.k.a. folders) don't always need to be written to the 
       zipfile themselves, because extracts add all of a file's dirs if
       needed (with os.makedirs(), in Python's zipfile module and the local
       zipsymlinks module).  Really, zipfiles don't have folders per se -
       just individual items with pathnames and metadata.

       However, dirs MUST be added to the zipfile themselves to either:
       1) Retain folders that are empty in the original.
       2) Retain the original modtimes of folders (see extract below).

       When added directly, the zipfile records folders as zero-length
       items with a trailing "/", and recreates the folder on extracts
       as needed.  Disable folder writes with "storedirs" if this proves
       incompatible with other tools (but it works fine with WinZip).

       Note that the os.walk()'s files list is really all non-dirs (which
       may include non-file items that should likely be excluded on some
       platforms), and non-link subdirs are always reached by the walker.
       Dir links are returned in subdir list, but not followed by default.
       [Update: per ahead[*], os.walk() was later replaced here with an 
       explicit-recursion coding, which visits directories more directly.]

    SYMLINKS: 
       If atlinks=True, this copies items links reference, not links themselves,
       and steps into subdirs referenced by links; else, it copies links and 
       doesn't follow them.  For links to dirs, os.walk() yields the name of 
       the link (not the dir it references), and this is the name under which
       the linked subdir is stored in the zip if atlinks (hence, dirs can be 
       present in multiple tree locations).  For example, if link 'python' 
       references dir 'python3', the latter is stored under the former name.
       [Update: the non-os.walk() recoding per ahead[*] behaves this same way.]

       This also traps recursive link paths to avoid running into memory errors
       or path limits, by using stat object st_ino unique identifiers to
       discern loops from valid dir repeats, where inode ids are supported.
       For more on recursive links detection, see isRecursiveLink() above.
       For more details on links in os.walk(), see docetc/symlinks/demo*.txt.

    WINDOWS LONG PATHS: 
       On Windows, very long paths are supported by prefixing all file-tool
       call paths with '\\?' and making them absolute, and passing these on to
       zipfile and zipsymlinks APIs for use in file-tool calls.  Names without
       \\?\ or absolute mapping are passed for use in the archive itself; this
       is required to support relative paths in the archive itself -- if not
       passed, archive names are created from filenames by running filenames
       though os.path.splitdrive() which drops the \\?\, but this does not
       translate from absolute back to relative (when users pass relative).

       [*]THIS ALSO required replacing the former os.walk() coding with explicit
       (manual) recursion.  os.walk() required the root to have a just-in-case 
       FWP() prefix to support arbitrary depth; which made os.walk() yield dirs
       that were always \\?\-prefixed and absolute; which in turn made all
       paths absolute in the zip archive.  Supporting relative zip paths
       AND long-paths requires either explicit recursion (used here) or an
       os.walk() coding with abs->rel mapping (which is possible, but may
       be preclusive: see the message display code in the extract ahead).

       Nit: the explicit-recursion recoding changes the order in which items
       are visited and added - it's now alphabetical per level on Mac OS HFS,
       instead of files-then-dirs (roughly).  This order is different but
       completely arbitrary: it impacts the order of messages output, but
       not the content or utility of the archive zipfile generated.  For
       the prior os.walk() variant, see ../docetc/longpaths/prior-code.

       Also nit: in the explicit-recursion recoding, links that are invalid 
       (do not point to an existing file or dir) are now an explicit case
       here.  Specifically, links to both nonexistent items and non-file/dir
       items are added to the zipfile, despite their rareness, and even if 
       "-atlinks" follow-links mode is used and the referent cannot be added. 
       This is done in part because Mergeall and cpall propagate such links
       too, but also because programs should never silently drop content for
       you: invalid links may have valid uses, and may refer to items present
       on another machine.  The former os.walk()-based version added such 
       links just because that call returns dirs and non-dirs, and invalid
       links appear in the latter. 

       Also also nit: more clearly a win, the new coding reports full paths 
       to cruft items; it's difficult to identify drops from basenames alone.
       See folder _algorithms here for alternative codings for this function.
    -----------------------------------------------------------------------
    """

    # 
    # handle this dir
    #
    if storedirs and thisdirpath != '.':
        # add folders too
        stats.folders += 1
        trace2('Adding folder', thisdirpath, thiszipatpath, trace)  
        zipfile.write(filename=FWP(thisdirpath),             # fwp for file tools
                      arcname=thiszipatpath)                 # not \\?\ + abs, -zip@?
        addModtimeUTC(zipfile, FWP(thisdirpath))             # UTC modtimes [1.2]

    # 
    # handle items here
    #
    for itemname in os.listdir(FWP(thisdirpath)):            # list (fixed windows) path
        itempath  = os.path.join(thisdirpath, itemname)      # extend real provided path
        zipatpath = os.path.join(thiszipatpath, itemname)    # possibly munged path [1.2]
        
        # 
        # handle subdirs (and links to them)
        #
        if os.path.isdir(FWP(itempath)):
            if isCruft(itemname, cruftpatts):                # match name, not path
                # skip cruft dirs
                stats.crufts += 1
                trace('--Skipped cruft dir', itempath)

            elif atlinks:
                # following links: follow? + add
                if isRecursiveLink(itempath):
                    # links to a parent: copy dir link instead
                    stats.links += 1
                    trace('Recursive link copied', itempath)
                    addSymlink(FWP(itempath), zipatpath, zipfile, trace)
                else:
                    # recur into dir or link
                    addEntireDir(itempath, zipfile,     
                                 stats, zipatpath, 
                                 storedirs, cruftpatts, atlinks, trace)

            else:
                # not following links
                if os.path.islink(FWP(itempath)):
                    # copy dir link
                    stats.links += 1 
                    trace2('Adding  link  ~folder', itempath, zipatpath, trace) 
                    addSymlink(FWP(itempath), zipatpath, zipfile, trace)               
                else:
                    # recur into dir
                    addEntireDir(itempath, zipfile, 
                                 stats, zipatpath,
                                 storedirs, cruftpatts, atlinks, trace)

        # 
        # handle files (and links to them)
        # 
        elif os.path.isfile(FWP(itempath)):
            if isCruft(itemname, cruftpatts):
                # skip cruft files
                stats.crufts += 1
                trace('--Skipped cruft file', itempath)

            elif atlinks:
                # following links: follow? + add
                stats.files += 1
                trace2('Adding  file ', itempath, zipatpath, trace)
                zipfile.write(filename=FWP(itempath),         # fwp for file tools
                              arcname=zipatpath)              # not \\?\ + abs, -zip@?
                addModtimeUTC(zipfile, FWP(itempath))         # UTC modtimes [1.2]

            else:
                # not following links
                if os.path.islink(FWP(itempath)):
                    # copy file link
                    stats.links += 1  
                    trace2('Adding  link  ~file', itempath, zipatpath, trace)
                    addSymlink(FWP(itempath), zipatpath, zipfile, trace)
                else:
                    # add simple file
                    stats.files += 1
                    trace2('Adding  file ', itempath, zipatpath, trace)
                    zipfile.write(filename=FWP(itempath),     # fwp for file tools
                                  arcname=zipatpath)          # name in archive, -zip@?
                    addModtimeUTC(zipfile, FWP(itempath))     # UTC modtimes [1.2]

        #
        # handle non-file/dir links (to nonexistents or oddities)
        #
        elif os.path.islink(FWP(itempath)):
            if isCruft(itemname, cruftpatts):
                # skip cruft non-file/dir links
                stats.crufts += 1
                trace('--Skipped cruft link', itempath)

            else:
                # copy link to other: atlinks or not
                stats.links += 1   
                trace2('Adding  link  ~unknown', itempath, zipatpath, trace)
                addSymlink(FWP(itempath), zipatpath, zipfile, trace)

        #
        # handle oddities (not links to them)
        #
        else:
            # ignore cruft: not adding this
            stats.unknowns += 1
            trace('--Skipped unknown type:', itempath)       # skip fifos, etc.

        # goto next item in this folder



#===============================================================================



def zipatmunge(sourcepath, zipat):
    """
    -----------------------------------------------------------------------
    [1.2] If zipat is not None, replace the entire dir path in sourcepath
    with the zipat path string.  This implements the "-zip@path" switch
    and function argument added in 1.2 to allow zipped paths (and hence
    later unzip paths) to be shortened, expanded, or dropped altogether. 

    Subtle things:
    - This is called for sources at the top level of a create only; 
      the tree-walk recursion extends the munged path at each level
    - sourceroot may be empty or '.' for source items in the CWD
    - zipat may be '.' for no nesting, and may be empty (same as '.')
    - The long-path prefix for Windows is not part of sourcepath here
    - For border cases, this relies on the fact that os.path.split('z') 
      returns ('', 'z'), and os.path.join('', 'z') returns 'z'.
    -----------------------------------------------------------------------
    """
    
    if zipat is None:
        return sourcepath    # zip@ not used, or zipat not passed

    assert isinstance(zipat, str)
    zipat = zipat.rstrip(os.sep)                               # drops trailing slash
    sourceroot, sourceitem = os.path.split(sourcepath)         # ditto, but implicit

    if sourceroot == '':                                       # source has no path:
        return os.path.join(zipat, sourcepath)                 #   concat zipat, if any
    elif zipat in ['.', '']:                                   # zipat is '.' or '': 
        return sourceitem                                      #   rm root path, if any
    else:                                                      # else replace root path
        return sourcepath.replace(sourceroot, zipat, 1)        # but just at the front



def trace2(message, filepath, zipatpath, trace):
    """
    -----------------------------------------------------------------------
    [1.2] Now that zipat allows zip paths to vary from original file 
    paths, show the zip path in output to clarify what was truly zipped.  
    This generally makes a post-zip list unnecessary to see results.

    The extra line is not printed if the before/after paths are the same
    (which matches pre-1.2 output); and it apes the '=>' format used for 
    extracts (which still always show a second line, because target path 
    is more crucial to disclose, even if it == zip path).  

    This also parrots most of the zipfile module's (and zipsymlinks.py's)
    transforms to zipatpath, to avoid spurious diffs (e.g., './x' != 'x'),
    and make the extra line's zip path match that of post-zip listings. 
    Avoids pretest '\' => '/' on Windows to minimize mismatches/lines,
    but the goal is a bit gray: true zip paths, or just flag -zip@ diffs?
    -----------------------------------------------------------------------
    """

    # mimic what zipfile will do
    arcname = os.path.splitdrive(zipatpath)[1]
    arcname = os.path.normpath(arcname)
    arcname = arcname.lstrip(os.sep + (os.altsep or ''))

    # but not this: filepath still has '\' on Windows!
    # arcname = arcname.replace(os.sep, "/")

    trace(message, filepath)
    if arcname != filepath:
        trace('\t\t=> %s' % arcname)    # sans leading '/\', '.', most '..', '\', 'c:'



#===============================================================================
    
    

def createzipfile(zipname,          # pathname of new zipfile to create
                  addnames,         # sequence of pathnames of items to add
                  storedirs=True,   # record dirs explicitly in zipfile?
                  cruftpatts={},    # cruft files skip/keep, or {}=do not skip
                  atlinks=False,    # zip items referenced instead of links?
                  trace=print,      # trace message router (or lambda *x: None)
                  zipat=None):      # alternate root zip path for all items [1.2]
    """
    -----------------------------------------------------------------------
    Make a zipfile at path "zipname" and add to it all folders and files
    in "addnames".  Its relative or absolute pathnames are propagated to
    the zipfile, to be used as path suffix when extracting to a target dir.
    See extractzipfile(), ../zip-create.py, and ../zip-extract.py for more
    docs on the use of relative and absolute pathnames for zip sources.

    Pass "trace=lambda *args: None" for silent operation.  See function
    addEntireDir() above for details on "storedirs" (its default is normally
    desired), and ahead here for "cruftpatts" and "atlinks" (their defaults
    include all cruft files and folders in the zip, and copy links instead
    of the items they reference, respectively).
    
    This always uses ZIP_DEFLATED, the "usual" zip compression scheme,
    and the only one supported in Python 2.X (ZIP_STORED is uncompressed).
    Python's base zipfile module used here supports Unicode filenames 
    automatically (encoded per UTF8).  

    [1.1] This now returns a CreateStats with #files/folders/links/unknowns
    and a repr for display when used in shell scripts (see class above).

    [1.1] ziptools run on Python 2.X forces filenames to unicode, so 2.X's
    zipfile module stores non-ASCII filenames in zips more portably; this
    avoids munged names in unzips run on 3.X and other tools.  For details, 
    see doctetc/1.1-upgrades/py-2.X-fixes.txt.

    WILDCARDS
       [1.1] Unlike the "../zip-create.py" command-line script, this function
       does not auto-glob addnames with unexpanded "*" (and other) operators.  
       Use Python's glob.glob() to expand names as needed before calling here, 
       and see the script and top-level README for pointers (it's a one-liner).

    CRUFT: 
       By default, all files and folders are added to the zip.  This is
       by design, because this code was written as a workaround for WinZip's
       silent file omissions.  As an option, though, this function will
       instead skip normally-hidden cruft files and folders (e.g., ".*")
       much like Mergeall, so they are not added to zips used to upload
       websites or otherwise distribute or transfer programs and data.  To
       enable cruft skipping, pass to cruftpatts a dictionary of this form:
    
          {'skip': ['pattern', ...],
           'keep': ['pattern', ...]}

       to define fnmatch filename patterns for both items to be skipped, and
       items to be kept despite matching a skip pattern (e.g., ".htaccess").
       If no dictionary is passed, all items are added to the zip; if either
       list is empty, it fails to match any file.  See zipcruft.py for more
       details, and customizable presets to import and pass to cruftpatts
       (the default is available as "cruft_skip_keep" from this module too).

    SYMLINKS: 
       Also by default, if symbolic links are present, they are added to 
       the zip themselves - not the items they reference.  Pass atlinks=True
       to instead follow links and zip the items they reference.  This also 
       traps recursive links if atlinks=True, where inodes are supported; see
       isRecursiveLink() above for more details.  As of version [1.1], creates
       now also properly set per-link permission bits in zipfiles, for extracts.

    LARGE FILES: 
       allowZip64=True supports files of size > 2G with ZIP64 extensions, 
       that are supported unevenly in other tools, but work fine with the 
       create and extract tools here.  It's True by default in Python 3.4+ 
       only; a False would prohibit large files altogether, which avoids 
       "unzip" issues but precludes use in supporting tools. 

       Per testing, some Unix "unzip"s fail with large files made here, but
       both the extract here and Mac's Finder-click unzips handle them well.
       Split zips into smaller parts iff large files fail in your tools, and
       you cannot find or install a recent Python 2.X or 3.X to run ziptools.
       Example publish-halves.py in learning-python.com/genhtml has pointers. 
    -----------------------------------------------------------------------
    """

    trace('Zipping', addnames, 'to', zipname)
    if cruftpatts:
        trace('Cruft patterns:', cruftpatts)
    stats = CreateStats()    # counts [1.1]
 
    #
    # handle top-level items
    #
    zipfile = ZipFile(zipname, mode='w', compression=ZIP_DEFLATED, allowZip64=True)
    for addname in addnames:
 
        # force Unicode in Python 2.X so non-ASCII interoperable [1.1]
        if RunningOnPython2:
            try:
                addname = addname.decode(encoding='UTF-8')    # same as unicode()
            except:
                trace('**Cannot decode "%s": skipped' % addname)
                continue

        # change zipped paths for top-level sources if -zip@/zipat [1.2]
        zipatpath = zipatmunge(addname, zipat)

        if (addname not in ['.', '..'] and
            isCruft(os.path.basename(addname), cruftpatts)):
            stats.crufts += 1
            trace('--Skipped cruft item', addname)

        elif os.path.islink(FWP(addname)) and not atlinks:
            stats.links += 1
            trace2('Adding  link  ~item', addname, zipatpath, trace)
            addSymlink(FWP(addname), zipatpath, zipfile, trace)

        elif os.path.isfile(FWP(addname)):
            stats.files += 1
            trace2('Adding  file ', addname, zipatpath, trace)
            zipfile.write(filename=FWP(addname), arcname=zipatpath)
            addModtimeUTC(zipfile, FWP(addname))    # UTC modtimes [1.2]

        elif os.path.isdir(FWP(addname)):
            addEntireDir(addname, zipfile,
                         stats, zipatpath,
                         storedirs, cruftpatts, atlinks, trace)

        else: # fifo, etc.
            stats.unknowns += 1
            trace('--Skipped unknown type:', addname)

    zipfile.close()
    return stats       # [1.1] printed at shell



#===============================================================================



def showpath(pathto, pathtoWasRelative):
    """
    -----------------------------------------------------------------------
    Extract helper: for message-display only, and on Windows only, try to
    undo the \\?\ prefix and to-absolute mapping for paths.  This may or 
    may not be exactly what was given, but is better than always showing 
    an absolute path in messages, and avoiding the just-in-case FWP() 
    described in extract() would require an extensive extract() rewrite.
    This used to be a nested function; it probably shouldn't have been.
    -----------------------------------------------------------------------
    """
    if RunningOnWindows:
        pathto = UFWP(pathto)                   # strip \\?\
        if pathtoWasRelative:
            pathto = os.path.relpath(pathto)    # relative to '.'
    return pathto



#===============================================================================



def extractzipfile(zipname,              # pathname of zipfile to extract from
                   pathto='.',           # pathname of folder to extract to
                   nofixlinks=False,     # do not translate symlink separators? 
                   trace=print,          # trace router (or lambda *p, **k: None)
                   permissions=False):   # propagate saved permisssions? [1.1]
    """
    -----------------------------------------------------------------------
    Unzip an entire zipfile at zipname to "pathto", which is created if
    it doesn't exist.  Items from the archive are stored under "pathto",
    using whatever subpaths with which they are recorded in the archive.
    
    Note that compression is passed for writing, but is auto-detected for
    reading here.  Pass "trace=lambda *p, **k: None" for silent operation.
    This function does no cruft-file skipping, as it is assumed to operate
    in tandem with the zip creation tools here; see Mergeall's script
    nuke-cruft-files.py to remove cruft in other tools' zips if needed.

    [1.1] This now returns an ExtractStats with #files/folders/links/unknowns
    and a repr for display when used in shell scripts (see class above).

    MODTIMES:
       At least through the latest 3.X, Python's zipfile library module does 
       record original files' modification times in the zipfiles it creates, 
       but does NOT retain files' original modification time when extracting:
       their modification times are all set to unzip time.  This is clearly 
       a defect, which will hopefully be addressed soon (a similar issue for
       permissions has been posted - see ahead).

       The workaround here manually propagates the files' original mod
       times in the zip as a post-extract step.  It's more code than an
       extractall(pathto), but this version works, and allows extracted
       files to be listed individually in the script's output,
    
       See this file's main docstring for details on symlinks support here;
       links and their paths are made portable between Unix and Windows by
       translating their path separators to the hosting platform's scheme,
       but "nofixlinks" can be used to suppress path separator replacement.

       UPDATE as of [1.2], errors while writing modtimes are ignored with a 
       message in output (the modtime isn't updated, but the extract proceeds).
       The only context in which this is known to happen is on Android's 2016 
       Nougat and earlier.  Modtime-update failures are silent elsewhere.
       It's unlikely that we'll try to update a symlink's modtime on pre-Oreo  
       Android (symlink creates fail and make a stub file), but it's handled.
       chmod also raises an error before Oreo, but it was already caught and 
       ignored with a message (and can be avoided by not using "-permissions").

    FOLDER MODTIMES: 
       Py docs suggest that os.utime() doesn't work for folders' modtime 
       on Windows, but it does.  Still, a simple extract would change all 
       non-empty folders' modtimes to the unzip time, just by virtue of 
       writing files into those folders.  This isn't an issue for Mergeall:
       only files compare by modtime, and dirs are just structural.  The 
       issue is avoided here, though, by resetting folder modtimes to their
       original values in the zipfile AFTER all files have been written.

       The net effect: assuming the zip records folders as individual items
       (see create above), this preserves original modtimes for BOTH files
       and folders across zips, unlike many other zip tools.  Cut-and-paste,
       drag-and-drop, and xcopy can also change folder modtimes on Windows,
       so be sure to zip folders that have not been copied this way if you
       wish to test this script's folder modtime retention.

    ABOUT SAVEPATH: 
       The written-to "savepath" returned by zipfile.extract() may not be 
       just os.path.join(pathto, filename).  extract() also removes any 
       leading slashes, Windows drive and UNC network names, and ".." 
       up-references in "filename" before appending it to "pathto", to ensure
       that the item is stored relative to "pathto" regardless of any absolute,
       drive- or server-rooted, or parent-relative names in the zipfile's items.
       zipfile.write() drops all but "..", which zipfile.extract() discards.
       The local extractSymlink() behaves like zipfile.extract() in this regard.

    WINDOWS LONG PATHS: 
       To support long pathnames on Windows, always prefixes the pathto target
       dir with '\\?\' on Windows (only), so that all file-tool calls in zipfile
       and zipsymlinks just work for too-long paths -- the length of paths 
       joined to archive names is unknown here.  This internal transform is 
       hidden from users in messages, by dropping the prefix and mapping pathto 
       back to relative if was not given as absolute initially (see showpath()).

    LARGE FILES: 
       allowZip64=True uses ZIP64 extensions which support very large files.  Such
       files are supported unevenly in other tools, but work with the create and 
       extract tools here.  It's True by default in Python 3.4+ only, and seems 
       unused when unzipping (ZIP64 fields are used).  See createzipfile() for more.

    PERMISSIONS: 
       UPDATE: as of [1.1], ziptools now manually propagates permissions on extracts 
       (unzips) for files, folders, and links, but only if this is explicitly 
       enabled via command/function arguments.  This option should generally 
       be used only when unzipping from zipfiles known to have originated on 
       Unix, and when unzipping back to Unix.  Most use cases that require 
       permissions to survive trips to/from zips probably will satisfy this 
       guideline.  More permissions notes:

       - This option is enabled on unzips only.  Zips have saved permissions 
         since 1.0, though zipsymlinks.py required a change in 1.1 to set 
         per-link permission bits (instead of using a constant).  

       - Not all filesystems support Unix-style permissions.  On exFAT, for 
         instance, os.chmod() silently fails to change anything, and this
         upgrade has no effect.  It's okay to copy a zipfile to/from exFAT, 
         but don't unzip on exFAT if you care about keeping permissions.

       - The new permissions argument is last, perhaps inconsistently, for
         1.0 compatibility.  Use keyword arguments to avoid future flux.

       - The related Mergeall system gets permissions propagation "for free"
         because it uses shutil.copystat() to copy metadata from one file to 
         another.  That's not an option here, because "from" is a zip entry.
         See Mergeall's code at https://learning-python.com/mergeall.html.

       [Former caveat's notes: 
          Python's zipfile module preserves Unix-style permissions on creates 
          (zips) but not extracts (unzips).  This is a known Python bug; see: 
          https://bugs.python.org/issue15795.  ziptools 1.0 didn't try to work 
          around this one because it's subtle (e.g., Unix permissions cannot be 
          applied if the zip host was not Unix, but the host-type code may not 
          be set reliably or correctly in all zips).  Preserving executable 
          permissions on items extracted from zipfiles may also be security risk,
          but that's not much of an excuse: it's fine for zips that you create.]

    MAC OS EXFAT BUG FIX: 
       There is a bizarre but real bug on Mac OS (discovered on El Capitan) 
       that requires utime() to be run *twice* to set modtimes on exFAT drive
       symlinks.  Details omitted here for space: see Mergeall's cpall.py script
       for background (https://learning-python.com/programs).  In short, modtime
       is usually updated by the second call, not first:

          >>> p = os.readlink('tlink')
          >>> t = os.lstat('tlink').st_mtime
          >>> os.symlink(p, '/Volumes/EXT256-1/tlink2')
          >>> os.utime('/Volumes/EXT256-1/tlink2', (t, t), follow_symlinks=False)
          >>> os.utime('/Volumes/EXT256-1/tlink2', (t, t), follow_symlinks=False)

       This incurs a rarely-run and harmless extra call for non-exFAT drives,
       but suffices to properly propagate modtimes to exFAT on Mac OS.

       UPDATE [1.1]: permissions aren't impacted by this bug (os.chmod() is 
       a no-op on exFAT, per above), but it also impacts exFAT _folder_ modtimes 
       on Mac OS (only files work properly on exFAT).  Fixed in 1.1 to uname() 
       twice for folders on Mac OS too.  There are a handful of ways to check
       for exFAT explicitly on Unix (e.g., lsvfs, mount, and df -T exfat), 
       but all require brittle output parsing, and none are portable to 
       Windows; accept the trivial uname()*2 speed hit on Mac OS instead.

    MODTIMES - DST AND TIMEZONE: 
       UPDATE: as of [1.2], ziptools now stores UTC timestamps for item
       modtimes in zip extra fields, and uses them instead of zip's "local 
       time" on extracts.  This means that modtimes of zipfiles zipped and 
       unzipped by ziptools are immune to changes in both DST and timezone.  
       For more details, see the README's "_README.html#utctimestamps12",
       and see module zipmodtimeutc.py for most of the implementation.
       The former local-time scheme is still used for zipfiles without UTC. 
        
       [Former caveat's notes: 
          Extracts here do nothing about adjusting modtimes of zipped items 
          for the local timezone and DST policy, except to pass -1 to Python's
          time.mktime()'s DST flag to defer to libraries.  The net effect may 
          or may not agree with another unzip tool, and does not address 
          timezone changes.  For more background, see this related note:
          https://learning-python.com/post-release-updates.html#unziptimes.]

    ILLEGAL FILENAME CHARACTERS
       For most filenames, illegal characters are munged to "_" on Windows,
       but a symlink with illegal filename characters will be skipped with 
       a message in the output (an unlikely case - see zipsymlinks.py).
    -----------------------------------------------------------------------
    """

    trace('Unzipping from', zipname, 'to', pathto)
    dirmodtimes = []
    stats = ExtractStats()

    # always prefix with \\?\ on Windows: joined-path lengths are unknown;
    # hence, on Windows 'savepath' result is also \\?\-prefixed and absolute;

    pathtoWasRelative = not os.path.isabs(pathto)   # user gave relative?
    pathto = FWP(pathto, force=True)                # add \\?\, make abs
    
    #
    # extract all items in zip
    #
    zipfile = ZipFile(zipname, mode='r', allowZip64=True)
    for zipinfo in zipfile.infolist():              # for all items in zip

        # 
        # extract one item
        #
        if isSymlink(zipinfo):
            # read/save link path: stubs on failures
            trace('(Link)', end=' ')
            savepath = extractSymlink(zipinfo, pathto, zipfile, nofixlinks, trace)
        else:
            # create file or dir: abort on failures
            savepath = zipfile.extract(zipinfo, pathto) 

        # unlike create, always show from+to paths here
        filename = zipinfo.filename                       # item's path in zip            
        trace('Extracted %s\n\t\t=> %s' %
            (filename, showpath(savepath, pathtoWasRelative)))

        # 
        # propagate permissions from/to Unix for all, iff enabled [1.1]
        #
        if permissions:
            try:                                          # create saved perms
                perms = zipinfo.external_attr >> 16       # to lower 16 bits
                if perms != 0:

                    if os.path.islink(savepath):
                        # mod link itself, where supported
                        # not on Windows, Py3.2 and earlier
                        # Mac OS bug moot: no-op on exFAT
 
                        if (hasattr(os, 'supports_follow_symlinks') and
                            os.chmod in os.supports_follow_symlinks):
                            os.chmod(savepath, perms, follow_symlinks=False)

                        # Unix Py 2.X and 3.2- have lchmod, but not f_s
                        elif hasattr(os, 'lchmod'):
                            os.lchmod(savepath, perms)

                    else:
                        # mod file or dir, where supported (exFAT=no-op)
                        os.chmod(savepath, perms) 
            except:
                trace('--Error setting permissions')         # e.g., pre-Oreo Android

        # 
        # propagate modtime to files, links (and dirs on some platforms)
        #
        datetime = getModtimeUTCorLocal(zipinfo, zipfile)    # UTC if present [1.2]

        if os.path.islink(savepath):
            # reset modtime of link itself where supported
            # but not on Windows or Py3.2-: keep now time
            # and call _twice_ on Mac for exFAT drives bug  

            stats.links += 1
            if (hasattr(os, 'supports_follow_symlinks') and  # iff utime does links
                os.utime in os.supports_follow_symlinks):
                try:
                    os.utime(savepath, (datetime, datetime), follow_symlinks=False)
                except:
                    trace('--Error setting link modtime')    # pre-Oreo Android [1.2]
                else:
                    # go again for Mac OS exFAT bug
                    if RunningOnMacOS:
                        os.utime(savepath, (datetime, datetime), follow_symlinks=False)

        elif os.path.isfile(savepath):
            # reset (non-link) file modtime now              # no Mac OS exFAT bug 
            stats.files += 1
            try:
                os.utime(savepath, (datetime, datetime))     # dest time = src time 
            except:
                trace('--Error setting file modtime')        # pre-Oreo Android [1.2]

        elif os.path.isdir(savepath):
            # defer (non-link) dir till after add files
            stats.folders += 1
            dirmodtimes.append((savepath, datetime))         # where supported

        else:
            # bad type in zipfile
            stats.unknowns += 1
            assert False, 'Unknown type extracted'           # should never happen

    # 
    # reset (non-link) dir modtimes now, post file adds
    #
    for (savepath, datetime) in dirmodtimes:
        try:
            os.utime(savepath, (datetime, datetime))         # reset dir mtime now
        except:                                              # pre-Oreo Android [1.2]
            trace('--Error settting folder modtime')
        else:                                                # but ok on Windows/Unix
            # go again for Mac OS exFAT bug [1.1]
            if RunningOnMacOS:
                os.utime(savepath, (datetime, datetime))

    zipfile.close()
    return stats       # to be printed at shell [1.1]



#===============================================================================

# see ../selftest.py for former __main__ code cut here for new pkg structure
