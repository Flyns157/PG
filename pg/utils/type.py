from sqlalchemy.types import TypeDecorator, String
from pydantic import HttpUrl

class HttpUrlType(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if isinstance(value, HttpUrl):
            return str(value)
        elif isinstance(value, str):
            return value
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return HttpUrl(value)
        return None
