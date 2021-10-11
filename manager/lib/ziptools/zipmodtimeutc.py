"""
================================================================================
zipmodtimeutc.py - zip/unzip UTC modtime timestamps via zip extra field [1.2].
See ziptools' ../_README.html for license, author, and other logistics.

ziptools 1.2 makes zipfile modtimes of files, folders, and symlinks immune 
to changes in both timezone and DST, by storing UTC timestamps in one of the 
"extra fields" defined by the zipfile standard.  

In particular, the extended-timestamp extra field (code 0x5455) introduced by 
the Info-ZIP project is ideal for this: ziptools adds one of these extra fields
to each items' central directory header on zips, and fetches them from the same 
location on unzips.  When present for any item, this field is used for propagated
modtime instead of the main MS-DOS "local time," and will simply be ignored by 
tools that don't support it.

This is a full fix to zip's local-time issues: UTC timestamps are relative to 
a fixed point, and thus both timezone and DST agnostic.  Local time is used for
display only, as it should be, and not for file metadata (in zips or elsewhere).
Given zips' lack of timezone info, UTC is the only way to make times accurate.

The prior scheme in ziptools 1.1 used the zip local time, and deferred to 
Python's library calls time.localtime() and time.mktime() to both translate 
UTC time to and from local time, and handle DST changes.  Unfortunately, that
scheme's results could vary from those of other zip tools on DST changes, and 
did nothing about timezone changes.  The new UTC timestamp extra-field scheme
resolves both DST and timezone modtime issues with a single fix.

FIELD LAYOUT:

Tip: 'zipinfo -V zipfile.zip' displays central-directory contents.
The layout of the extra field per spec, all little-endian byte order:

  Value        Size     Description
  -----        ----     -----------
  0x5455       Short    tag for this extra block type ("UT")
  TSize        Short    total data size for this block
  Flags        Byte     info bits (refers to local header, not this)
  (ModTime)    Long     time of last modification (UTC/GMT)

Where TSize designates modtime central-directory presence, 
and Flags describes the local entry correspondence as follows:

  bit 0       if set, modification time is present
  bit 1       if set, access time is present
  bit 2       if set, creation time is present
  bits 3-7    reserved for additional timestamps; not set

LIBRARY DEPENDENCE:

The lack of direct support for extra fields and arguably walled-in coding 
structure of Python's zipfile module renders the code here subtle.  In 
fact, the reliance here on infolist()[-1] may qualify as a hack, and the
use of getinfo() seems a bit magical.  These are public and documented
APIs, and avoiding them would require massive rewrites here.  Still, the 
coupling is tight, and this code may grow module-version dependent in time.

As is, the code here has been verified to work for zipfile in Python 2.7, 
3.5, and 3.7, but open-source code can morph arbitrarily; forking a Python
standard library is a nonstarter; and a frozen executable isn't yet an 
option here (ziptools is a programmer's library too).  If a future zipfile
mod breaks this code, the fix is to use an older Python and/or zipfile.

OTHER CAVEATS: 

1) Scope: the new UTC scheme won't help for zipfiles created by tools that 
don't record the extra field; in these cases, ziptools falls back on the 
original 1.1 local-time scheme.  If other zip tools add UTC modtimes in
the central directory's 0x5455 fields, ziptools will make use of them.

2) Field use: It is unclear whether the 0o5455 field should appear in a 
local file header, central directory header, or both.  It's stored in 
the central directory only here, and seems to pass in other tools.
Storing in the local header too may require manual ZipInfo builds.

3) Other fields: besides 0x5455, others extra fields may contain extended 
timestamps too, but ziptools doesn't process these because it doesn't add them.
ziptools also doesn't do anything about creation or access time in its 0x5455
fields, because they are generally too variable across platforms (and can't 
show up in the central directory's headers in any event)  Such support could
be added if there's any user interest; at present, it lacks use cases.

4) Subclassing: this could have been coded as a ZipFile subclass, of course 
(e.g., extending the close() method would save a few manual calls).  This 
wasn't pursued, because the symlinks support is already coded as functions, 
and it was a goal to make this as independent of zipfile's API as possible; 
it's changed in the past, and is prone to change again.
================================================================================
"""

from __future__ import print_function         # run on python 2.x too
import os, time, struct

# show ops or not (this file only)
#trace = lambda *args: print('='* 4, *args)
trace = lambda *args: None

UTCExtraCode  = 0x5455     # extended timestamp ('UT'), introduced by Info-ZIP project
UTCExtraFlags = 0b0000     # no local-header extra fields: just in central directory

AllExtraHdrFmt = '<HH'     # code + length: 2 unsigned 2-byte shorts, little endian
AllExtraHdrLen = 4

UTCExtraDataFmt = '<Bl'    # flags + timestamp: unsigned byte + signed 4-byte long, little
UTCExtraDataLen = 5


#===============================================================================



def addModtimeUTC(zipfile, filepath=None, utcmodtime=None):
    """
    --------------------------------------------------------------------------
    On Zips: add an extra field for the item just written, with an extended 
    timestamp value passed to utcmodtime or read from filepath - filesystem
    UTC time of the original item.  The field added to a zipinfo here is 
    later written to the item's central-directory entry on zipfile.close().

    Called just after a zip write, and assumes the item written was appended 
    to infolist (else need to build ZipInfos for files and folders manually).
    os.path.getmtime() is the same as os.stat().st_mtime, but symlinks must
    must pass in a link's own time garnered from its os.lstat().st_mtime.
    filepath already has the Windows long-path prefix on that platform.
    --------------------------------------------------------------------------
    """
    assert not filepath or not utcmodtime

    zipinfo = zipfile.infolist()[-1]                         # the item just written
    utcmodtime = utcmodtime or os.path.getmtime(filepath)    # passed (symlinks) or not

    extrabytes =  struct.pack(AllExtraHdrFmt, UTCExtraCode, UTCExtraDataLen)
    extrabytes += struct.pack(UTCExtraDataFmt, UTCExtraFlags, int(utcmodtime))

    trace('Added UTC timestamp:', repr(extrabytes))
    zipinfo.extra += extrabytes    # to be written on zipfile.close()



#===============================================================================



def getModtimeUTCorLocal(zipinfo, zipfile):
    """
    --------------------------------------------------------------------------
    On unzips: return the UTC modtime timestamp for the item represented by 
    zipinfo in zipfile - from either the extra UTC timestamp field, or zip's
    local time.  If present, UTC timestamps are in the extra fields of each 
    item's central-directory entry.  The extra fields are read (not parsed)
    by zipfile's __init__(), and tabled by filename (getinfo() is a dict []).
    --------------------------------------------------------------------------
    """

    localextra = zipinfo.extra                                # from file local header
    centralextra = zipfile.getinfo(zipinfo.filename).extra    # from central directory
    extrabytes = centralextra                                 # choose wisely?...

    utctime = None
    try:
        # 
        # use UTC timestamp extra field if present, instead of local time;
        # parse through extra-field bytes till timestamp found or no more;
        #
        offset = 0
        while offset < len(extrabytes):
            hdrbytes = extrabytes[offset : offset + AllExtraHdrLen]
            offset += AllExtraHdrLen
            code, length = struct.unpack(AllExtraHdrFmt, hdrbytes)
            if code != UTCExtraCode:
                offset += length
            else:
                databytes = extrabytes[offset : offset + UTCExtraDataLen]
                flags, utctime = struct.unpack(UTCExtraDataFmt, databytes)
                trace('Got UTC timestamp:', utctime)
                break
        else:
            trace('No UTC timestamp found: used local')

    except Exception as why:
        #
        # bad extra-field formatting (e.g., null byte at end)
        # use local, continue unzipping rest of the archive
        #
        trace('Error parsing extra fields: used local')
        trace('Python exception:', why)

    if utctime is None:
        #
        # not found or error: fall back on pre 1.2 scheme: use main 
        # zip local time, and defer to time.mktime() to covert to UTC 
        # as possible (adjusts for DST maybe, but never for timezones);
        #
        localtime = zipinfo.date_time                      # zip's 6-tuple
        utctime   = time.mktime(localtime + (0, 0, -1))    # 9-tuple=>float

    return utctime    # to be propogated to unzipped item

