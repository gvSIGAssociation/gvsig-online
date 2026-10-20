from .rest_geoserver import RequestError, UploadError

class UnsupportedRequestError(Exception):
    pass

class BadFormat(UploadError):
    pass

class WrongElevationPattern(UploadError):
    pass

class WrongTimePattern(UploadError):
    pass

class InvalidValue(RequestError):
    pass

class UserInputError(UploadError):
    pass