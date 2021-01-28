"""DBF header definition.

TODO:
  - handle encoding of the character fields
    (encoding information stored in the DBF header)

"""
"""History (most recent first):
14-dec-2010 [als]   added Memo file support
16-sep-2010 [als]   fromStream: fix century of the last update field
11-feb-2007 [als]   added .ignoreErrors
10-feb-2007 [als]   added __getitem__: return field definitions
                    by field name or field number (zero-based)
04-jul-2006 [als]   added export declaration
15-dec-2005 [yc]    created
"""

__version__ = "$Revision: 1.7 $"[11:-2]
__date__ = "$Date: 2010/12/14 11:07:45 $"[7:-2]

__all__ = ["DbfHeader"]

import cStringIO
import datetime
import struct
import time

import fields
from utils import getDate


class DbfHeader(object):
    """Dbf header definition.

    For more information about dbf header format visit
    `http://www.clicketyclick.dk/databases/xbase/format/dbf.html#DBF_STRUCT`

    Examples:
        Create an empty dbf header and add some field definitions:
            dbfh = DbfHeader()
            dbfh.addField(("name", "C", 10))
            dbfh.addField(("date", "D"))
            dbfh.addField(DbfNumericFieldDef("price", 5, 2))
        Create a dbf header with field definitions:
            dbfh = DbfHeader([
                ("name", "C", 10),
                ("date", "D"),
                DbfNumericFieldDef("price", 5, 2),
            ])

    """

    __slots__ = ("signature", "fields", "lastUpdate", "recordLength",
        "recordCount", "headerLength", "changed", "_ignore_errors")

    ## instance construction and initialization methods

    def __init__(self, fields=None, headerLength=0, recordLength=0,
        recordCount=0, signature=0x03, lastUpdate=None, ignoreErrors=False,
    ):
        """Initialize instance.

        Arguments:
            fields:
                a list of field definitions;
            recordLength:
                size of the records;
            headerLength:
                size of the header;
            recordCount:
                number of records stored in DBF;
            signature:
                version number (aka signature). using 0x03 as a default meaning
                "File without DBT". for more information about this field visit
                ``http://www.clicketyclick.dk/databases/xbase/format/dbf.html#DBF_NOTE_1_TARGET``
            lastUpdate:
                date of the DBF's update. this could be a string ('yymmdd' or
                'yyyymmdd'), timestamp (int or float), datetime/date value,
                a sequence (assuming (yyyy, mm, dd, ...)) or an object having
                callable ``ticks`` field.
            ignoreErrors:
                error processing mode for DBF fields (boolean)

        """
        self.signature = signature
        if fields is None:
            self.fields = []
        else:
            self.fields = list(fields)
        self.lastUpdate = getDate(lastUpdate)
        self.recordLength = recordLength
        self.headerLength = headerLength
        self.recordCount = recordCount
        self.ignoreErrors = ignoreErrors
        # XXX: I'm not sure this is safe to
        # initialize `self.changed` in this way
        self.changed = bool(self.fields)

    # @classmethod
    def fromString(cls, string):
        """Return header instance from the string object."""
        return cls.fromStream(cStringIO.StringIO(str(string)))
    fromString = classmethod(fromString)

    # @classmethod
    def fromStream(cls, stream):
        """Return header object from the stream."""
        stream.seek(0)
        _data = stream.read(32)
        (_cnt, _hdrLen, _recLen) = struct.unpack("<I2H", _data[4:12])
        #reserved = _data[12:32]
        _year = ord(_data[1])
        if _year < 80:
            # dBase II started at 1980.  It is quite unlikely
            # that actual last update date is before that year.
            _year += 2000
        else:
            _year += 1900
        ## create header object
        _obj = cls(None, _hdrLen, _recLen, _cnt, ord(_data[0]),
            (_year, ord(_data[2]), ord(_data[3])))
        ## append field definitions
        # position 0 is for the deletion flag
        _pos = 1
        _data = stream.read(1)
        while _data[0] != "\x0D":
            _data += stream.read(31)
            _fld = fields.lookupFor(_data[11]).fromString(_data, _pos)
            _obj._addField(_fld)
            _pos = _fld.end
            _data = stream.read(1)
        return _obj
    fromStream = classmethod(fromStream)

    ## properties

    year = property(lambda self: self.lastUpdate.year)
    month = property(lambda self: self.lastUpdate.month)
    day = property(lambda self: self.lastUpdate.day)

    @property
    def hasMemoField(self):
        """True if at least one field is a Memo field"""
        for _field in self.fields:
            if _field.isMemo:
                return True
        return False

    def ignoreErrors(self, value):
        """Update `ignoreErrors` flag on self and all fields"""
        self._ignore_errors = value = bool(value)
        for _field in self.fields:
            _field.ignoreErrors = value
    ignoreErrors = property(
        lambda self: self._ignore_errors,
        ignoreErrors,
        doc="""Error processing mode for DBF field value conversion

        if set, failing field value conversion will return
        ``INVALID_VALUE`` instead of raising conversion error.

        """)

    ## object representation

    def __repr__(self):
        _rv = """\
Version (signature): 0x%02x
        Last update: %s
      Header length: %d
      Record length: %d
       Record count: %d
 FieldName Type Len Dec
""" % (self.signature, self.lastUpdate, self.headerLength,
    self.recordLength, self.recordCount)
        _rv += "\n".join(
            ["%10s %4s %3s %3s" % _fld.fieldInfo() for _fld in self.fields]
        )
        return _rv

    ## internal methods

    def _addField(self, *defs):
        """Internal variant of the `addField` method.

        This method doesn't set `self.changed` field to True.

        Return value is a length of the appended records.
        Note: this method doesn't modify ``recordLength`` and
        ``headerLength`` fields. Use `addField` instead of this
        method if you don't exactly know what you're doing.

        """
        # insure we have dbf.DbfFieldDef instances first (instantiation
        # from the tuple could raise an error, in such a case I don't
        # wanna add any of the definitions -- all will be ignored)
        _defs = []
        _recordLength = self.recordLength
        for _def in defs:
            if isinstance(_def, fields.DbfFieldDef):
                _obj = _def
            else:
                (_name, _type, _len, _dec) = (tuple(_def) + (None,) * 4)[:4]
                _cls = fields.lookupFor(_type)
                _obj = _cls(_name, _len, _dec, _recordLength,
                    ignoreErrors=self._ignore_errors)
            _recordLength += _obj.length
            _defs.append(_obj)
        # and now extend field definitions and
        # update record length
        self.fields += _defs
        return (_recordLength - self.recordLength)

    def _calcHeaderLength(self):
        """Update self.headerLength attribute after change to header contents
        """
        # recalculate headerLength
        _hl = 32 + (32 * len(self.fields)) + 1
        if self.signature == 0x30:
            # Visual FoxPro files have 263-byte zero-filled field for backlink
            _hl += 263
        # bug#15: don't reduce existing header size
        if _hl > self.headerLength:
            self.headerLength = _hl

    ## interface methods

    def setMemoFile(self, memo):
        """Attach MemoFile instance to all memo fields; check header signature
        """
        _has_memo = False
        for _field in self.fields:
            if _field.isMemo:
                _field.file = memo
                _has_memo = True
        # for signatures list, see
        # http://www.clicketyclick.dk/databases/xbase/format/dbf.html#DBF_NOTE_1_TARGET
        # http://www.dbf2002.com/dbf-file-format.html
        # If memo is attached, will use 0x30 for Visual FoxPro file,
        # 0x83 for dBASE III+.
        if _has_memo \
        and (self.signature not in (0x30, 0x83, 0x8B, 0xCB, 0xE5, 0xF5)):
            if memo.is_fpt:
                self.signature = 0x30
            else:
                self.signature = 0x83
        self._calcHeaderLength()

    def addField(self, *defs):
        """Add field definition to the header.

        Examples:
            dbfh.addField(
                ("name", "C", 20),
                dbf.DbfCharacterFieldDef("surname", 20),
                dbf.DbfDateFieldDef("birthdate"),
                ("member", "L"),
            )
            dbfh.addField(("price", "N", 5, 2))
            dbfh.addField(dbf.DbfNumericFieldDef("origprice", 5, 2))

        """
        if not self.recordLength:
            self.recordLength = 1
        self.recordLength += self._addField(*defs)
        self._calcHeaderLength()
        self.changed = True

    def write(self, stream):
        """Encode and write header to the stream."""
        stream.seek(0)
        stream.write(self.toString())
        stream.write("".join([_fld.toString() for _fld in self.fields]))
        stream.write(chr(0x0D))   # cr at end of all hdr data
        _pos = stream.tell()
        if _pos < self.headerLength:
            stream.write("\0" * (self.headerLength - _pos))
        self.changed = False

    def toString(self):
        """Returned 32 chars length string with encoded header."""
        # FIXME: should keep flag and code page marks read from file
        if self.hasMemoField:
            _flag = "\x02"
        else:
            _flag = "\0"
        _codepage = "\0"
        return struct.pack("<4BI2H",
            self.signature,
            self.year - 1900,
            self.month,
            self.day,
            self.recordCount,
            self.headerLength,
            self.recordLength) + "\0" * 16 + _flag + _codepage + "\0\0"

    def setCurrentDate(self):
        """Update ``self.lastUpdate`` field with current date value."""
        self.lastUpdate = datetime.date.today()

    def __getitem__(self, item):
        """Return a field definition by numeric index or name string"""
        if isinstance(item, basestring):
            _name = item.upper()
            for _field in self.fields:
                if _field.name == _name:
                    return _field
            else:
                raise KeyError(item)
        else:
            # item must be field index
            return self.fields[item]

# vim: et sts=4 sw=4 :
