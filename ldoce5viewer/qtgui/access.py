"""application-specific URI scheme handler for QtWebKit"""

import imp
import os.path
import sys
import traceback

from PyQt5.QtCore import QBuffer
from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestJob,
    QWebEngineUrlSchemeHandler,
)

from .. import __name__ as basepkgname
from .. import __version__
from ..ldoce5 import LDOCE5, ArchiveError, FilemapError, NotFoundError
from ..utils.text import enc_utf8
from .advanced import search_and_render
from .config import get_config

# from .utils import fontfallback

STATIC_REL_PATH = "static"

_static_cache = {}


def _load_static_data(filename):
    """Load a static file from the 'static' directory"""

    if filename in _static_cache:
        return _static_cache[filename]

    is_frozen = hasattr(sys, "frozen") or imp.is_frozen(  # new py2exe
        "__main__"
    )  # tools/freeze

    if is_frozen:
        if sys.platform.startswith("darwin"):
            path = os.path.join(
                os.path.dirname(sys.executable),
                "../Resources",
                STATIC_REL_PATH,
                filename,
            )
        else:
            path = os.path.join(
                os.path.dirname(sys.executable), STATIC_REL_PATH, filename
            )
        with open(path, "rb") as f:
            data = f.read()
    else:
        try:
            from pkgutil import get_data as _get
        except ImportError:
            from pkg_resources import resource_string as _get

        data = _get(basepkgname, os.path.join(STATIC_REL_PATH, filename))

    if filename.endswith(".css"):
        s = data.decode("utf-8")
        # s = fontfallback.css_replace_fontfamily(s)
        data = s.encode("utf-8")
    elif filename.endswith(".html"):
        s = data.decode("utf-8")
        s = s.replace("{% current_version %}", __version__)
        data = s.encode("utf-8")

    _static_cache[filename] = data
    return data


class MyUrlSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, parent, searcher_hp=None, searcher_de=None):
        super().__init__(parent)
        self._searcher_hp = searcher_hp
        self._searcher_de = searcher_de
        config = get_config()
        self._ldoce5 = LDOCE5(config.get("dataDir", ""), config.filemap_path)

    def update_searcher(self, searcher_hp, searcher_de):
        self._searcher_hp = searcher_hp
        self._searcher_de = searcher_de

    def get_ldoce_content(self, path):
        (data, mime) = self._ldoce5.get_content(path)
        return (data, mime)

    def requestStarted(self, job: QWebEngineUrlRequestJob):
        url = job.requestUrl()
        scheme = url.scheme()
        mime = "text/html"
        data = b""

        if scheme == "dict":
            try:
                path = url.path().split("#", 1)[0]
                (data, mime) = self._ldoce5.get_content(path)
                mime = "text/html"
            except NotFoundError:
                data = b"<h2>Content Not Found</h2>"
                mime = "text/html"
            except FilemapError:
                data = b"<h2>File-Location Map Not Available</h2>"
                mime = "text/html"
            except ArchiveError:
                data = b"<h2>Dictionary Data Not Available</h2>"
                mime = "text/html"
        elif scheme == "static":
            try:
                data = _load_static_data(url.path().lstrip("/"))
                mime = ""
            except EnvironmentError:
                data = b"<h2>Static File Not Found</h2>"
                mime = "text/html"
        elif scheme == "search":
            searcher_hp = self._searcher_hp
            searcher_de = self._searcher_de
            if searcher_hp and searcher_de:
                try:
                    data = enc_utf8(search_and_render(url, searcher_hp, searcher_de))
                    mime = "text/html"
                except Exception:
                    s = u"<h2>Error</h2><div>{0}</div>".format(
                        "<br>".join(traceback.format_exc().splitlines())
                    )
                    data = enc_utf8(s)
                    mime = "text/html"
            else:
                mime = "text/html"
                data = b"<p>The full-text search index has not been created yet or broken.</p>"
        else:
            job.fail(QWebEngineUrlRequestJob.Error.RequestAborted)

        buffer = QBuffer(job)
        buffer.open(QBuffer.OpenModeFlag.ReadWrite)
        buffer.write(data or b"")
        buffer.seek(0)
        job.reply(mime.encode("ascii"), buffer)


# class MyNetworkAccessManager(QNetworkAccessManager):
#     """Customized NetworkAccessManager"""
#
#     def __init__(self, parent, searcher_hp, searcher_de):
#         QNetworkAccessManager.__init__(self, parent)
#         self._searcher_hp = searcher_hp
#         self._searcher_de = searcher_de
#
#     def createRequest(self, operation, request, data):
#         if operation == self.GetOperation and request.url().scheme() in (
#             "dict",
#             "static",
#             "search",
#         ):
#             return MyNetworkReply(
#                 self, operation, request, self._searcher_hp, self._searcher_de
#             )
#         else:
#             return super(MyNetworkAccessManager, self).createRequest(
#                 operation, request, data
#             )
#
#
# class MyNetworkReply(QNetworkReply):
#     """Customized NetworkReply
#
#     It handles the 'dict' and 'static' schemes.
#     """
#
#     def __init__(self, parent, operation, request, searcher_hp, searcher_de):
#         QNetworkReply.__init__(self, parent)
#
#         url = request.url()
#         self.setRequest(request)
#         self.setUrl(url)
#         self.setOperation(operation)
#         self.open(QIODevice.ReadOnly)
#
#         self._finished = False
#         self._data = None
#         self._offset = 0
#
#         self._url = url
#         self._searcher_hp = searcher_hp
#         self._searcher_de = searcher_de
#         QTimer.singleShot(0, self._load)  # don't disturb the UI thread
#
#     def _load(self):
#         url = self._url
#         config = get_config()
#         searcher_hp = self._searcher_hp
#         searcher_de = self._searcher_de
#         mime = None
#         error = False
#
#         if url.scheme() == "static":
#             try:
#                 self._data = _load_static_data(url.path().lstrip("/"))
#             except EnvironmentError:
#                 self._data = "<h2>Static File Not Found</h2>"
#                 mime = "text/html"
#                 error = True
#
#         elif url.scheme() == "dict":
#             try:
#                 path = url.path().split("#", 1)[0]
#                 ldoce5 = LDOCE5(config.get("dataDir", ""), config.filemap_path)
#                 (self._data, mime) = ldoce5.get_content(path)
#             except NotFoundError:
#                 self._data = "<h2>Content Not Found</h2>"
#                 mime = "text/html"
#                 error = True
#             except FilemapError:
#                 self._data = "<h2>File-Location Map Not Available</h2>"
#                 mime = "text/html"
#                 error = True
#             except ArchiveError:
#                 self._data = "<h2>Dictionary Data Not Available</h2>"
#                 mime = "text/html"
#                 error = True
#
#         elif url.scheme() == "search":
#             if searcher_hp and searcher_de:
#                 try:
#                     self._data = enc_utf8(
#                         search_and_render(url, searcher_hp, searcher_de)
#                     )
#                     mime = "text/html"
#                 except:
#                     s = u"<h2>Error</h2><div>{0}</div>".format(
#                         "<br>".join(traceback.format_exc().splitlines())
#                     )
#                     self._data = enc_utf8(s)
#                     mime = "text/html"
#                     error = True
#             else:
#                 mime = "text/html"
#                 self._data = (
#                     """<p>The full-text search index """
#                     """has not been created yet or broken.</p>"""
#                 )
#                 error = True
#
#         if mime:
#             self.setHeader(QNetworkRequest.ContentTypeHeader, mime)
#         self.setHeader(QNetworkRequest.ContentLengthHeader, len(self._data))
#         self.setOpenMode(self.ReadOnly | self.Unbuffered)
#
#         if error:
#             nwerror = QNetworkReply.ContentNotFoundError
#             error_msg = u"Content Not Found"
#             self.setError(nwerror, error_msg)
#             QMetaObject.invokeMethod(
#                 self,
#                 "error",
#                 Qt.QueuedConnection,
#                 Q_ARG(QNetworkReply.NetworkError, nwerror),
#             )
#
#         QMetaObject.invokeMethod(self, "metaDataChanged", Qt.QueuedConnection)
#         QMetaObject.invokeMethod(
#             self,
#             "downloadProgress",
#             Qt.QueuedConnection,
#             Q_ARG("qint64", len(self._data)),
#             Q_ARG("qint64", len(self._data)),
#         )
#         QMetaObject.invokeMethod(self, "readyRead", Qt.QueuedConnection)
#         QMetaObject.invokeMethod(self, "finished", Qt.QueuedConnection)
#
#         self._finished = True
#
#     def isFinished(self):
#         return self._finished
#
#     def isSequential(self):
#         return True
#
#     def abort(self):
#         self.close()
#
#     def size(self):
#         return len(self._data)
#
#     def bytesAvailable(self):
#         return (
#             super(MyNetworkReply, self).bytesAvailable()
#             + len(self._data)
#             - self._offset
#         )
#
#     def readData(self, maxSize):
#         size = min(maxSize, len(self._data) - self._offset)
#         data = self._data[self._offset : self._offset + size]
#         self._offset += size
#         return data
#
