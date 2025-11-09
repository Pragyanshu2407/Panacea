"""
Local shim for removed stdlib 'cgi' to satisfy legacy Django imports.
Implements 'parse_header' used by Django for Content-Type parsing.
"""
from email.message import Message
import re


def parse_header(header_value: str):
    msg = Message()
    # Using a known header to leverage email parser
    msg.add_header('Content-Type', header_value or '')
    content_type = msg.get_content_type()
    # get_params returns list of (key, value), first is the content-type itself
    params = dict((k, v) for k, v in msg.get_params(header='content-type') if k)
    return content_type, params


_boundary_re = re.compile(r"^[ -~]{1,200}$")  # printable ASCII, max 200 chars


def valid_boundary(boundary):
    """Approximate legacy cgi.valid_boundary used by Django.

    Accepts printable ASCII up to 200 chars; rejects empty or non-string.
    """
    if boundary is None:
        return False
    if isinstance(boundary, bytes):
        try:
            boundary = boundary.decode('ascii', errors='strict')
        except Exception:
            return False
    if not isinstance(boundary, str):
        return False
    return _boundary_re.match(boundary) is not None