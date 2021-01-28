"""Memo file support.

"""
"""History (most recent first):
13-dec-2010 [als]   created
"""

__version__ = "$Revision: 1.3 $"[11:-2]
__date__ = "$Date: 2010/12/15 08:08:23 $"[7:-2]

# Note: the data class is exported for TYPE constants.
__all__ = ["MemoFile", "MemoData"]

import os
import struct

class MemoData(str):

    """Data read from or written to Memo file.

    This is 8-bit string data with additional attribute
    type which can accept values of the TYPE_* constants.

    """

    TYPE_PICTURE = 0
    TYPE_MEMO = 1
    TYPE_OBJECT = 2
    TYPE_NULL = 160

    type = TYPE_MEMO

    def __new__(cls, value, type=TYPE_MEMO):
        _obj = super(MemoData, cls).__new__(cls, value)
        _obj.type = type
        return _obj

class MemoFile(object):

    """Memo file object"""

    __slots__ = ("name", "stream", "is_fpt", "blocksize", "tail")

    # End Of Text
    EOT = "\x1A\x1A"

    def __init__(self, f, blocksize=512, fpt=True,
            readOnly=False, new=False,
    ):
        """Initialize instance.

        Arguments:
            f:
                Filename or file-like object.
            blocksize:
                Size of blocks in the Memo file.
                Used for new files only; ignored if file already exists.
            fpt:
                True if file format is FoxPro Memo file
                (file blocks start with type and length fields).
            readOnly:
                If True, open existing files read-only.
                Ignored if ``f`` is a file object of if ``new`` is True.
            new:
                True to create new memo file,
                False to open existing file.

        """
        self.is_fpt = fpt
        if isinstance(f, basestring):
            # a filename
            self.name = f
            if new:
                self.stream = file(f, "w+b")
            else:
                self.stream = file(f, ("r+b", "rb")[bool(readOnly)])
        else:
            # a stream
            self.name = getattr(f, "name", "")
            self.stream = f
        self.stream.seek(0)
        if new:
            if not self.is_fpt:
                self.blocksize = 512
            # http://msdn.microsoft.com/en-US/library/d6e1ah7y%28v=VS.80%29.aspx
            elif blocksize == 0:
                self.blocksize = 1
            elif blocksize <= 32:
                self.blocksize = 512 * blocksize
            else:
                self.blocksize = blocksize
            self.tail = 512 / self.blocksize
            self.stream.write(
                struct.pack(">LHH", self.tail, 0, self.blocksize)
                + "\0" * 8 + "\x03" + "\0" * 495)
        else:
            (self.tail, _zero, self.blocksize) = struct.unpack(">LHH",
                self.stream.read(8))
            if not self.is_fpt:
                # In DBT files, block size is fixed to 512 bytes
                self.blocksize = 512

    @staticmethod
    def memoFileName(name, isFpt=True):
        """Return Memo file name for given DBF file name

        Arguments:
            name:
                Name of DBF file.  FoxPro file extensions
                like SCX or DBC are supported.
            isFpt:
                True if file is FoxPro Memo file.
                If isFpt is False, DBF memos have
                extension DBT instead of FPT.

        """
        (_basename, _ext) = os.path.splitext(name)
        if _ext.upper() in ("", ".DBF"):
            if isFpt:
                return _basename + ".FPT"
            else:
                return _basename + ".DBT"
        else:
            return name[:-1] + "T"

    def read(self, blocknum):
        """Read the block addressed by blocknum

        Return a MemoData object.

        """
        self.stream.seek(self.blocksize * blocknum)
        if self.is_fpt:
            (_type, _len) = struct.unpack(">LL", self.stream.read(8))
            if _type == MemoData.TYPE_NULL:
                _value = ''
            else:
                _value = self.stream.read(_len)
        else: # DBT
            _type = MemoData.TYPE_MEMO
            self.stream.seek(self.blocksize * blocknum)
            _value = ''
            while self.EOT not in _value:
                _value += self.stream.read(self.blocksize)
            _value = _value[:_value.find(self.EOT)]
        return MemoData(_value, _type)

    def write(self, value):
        """Write a value to FPT file, return starting block number

        The value argument may be simple string or a MemoData object.
        In the former case value type is assumed to be TYPE_MEMO.

        """
        _rv = self.tail
        self.stream.seek(self.blocksize * _rv)
        if self.is_fpt:
            _length = len(value) + 8
            _type = getattr(value, "type", MemoData.TYPE_MEMO)
            self.stream.write(struct.pack(">LL", _type, len(value)) + value)
        else:
            _length = len(value) + 2
            self.stream.write(value + self.EOT)
        #_cnt = int(math.ceil(float(_length) / self.blocksize))
        _cnt = (_length + self.blocksize - 1) / self.blocksize
        self.stream.write("\0" * (_cnt * self.blocksize - _length))
        self.tail += _cnt
        self.stream.seek(0)
        self.stream.write(struct.pack(">L", self.tail))
        return _rv

    def flush(self):
        """Flush data to the associated stream."""
        self.stream.flush()

# vim: et sts=4 sw=4 :
