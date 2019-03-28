#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.bridge import XInstanceProvider
from com.sun.star.container import XChild
from com.sun.star.io import XInputStreamProvider
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import IllegalIdentifierException
from com.sun.star.ucb import XContentIdentifier
from com.sun.star.ucb import XContentIdentifierFactory
from com.sun.star.util import XLinkUpdate
from com.sun.star.util import XUpdatable

from .unolib import Initialization
from .unolib import PropertySet
from .contenttools import createContent
from .contenttools import createContentIdentifier
from .contenttools import getUri
from .unotools import getNamedValueSet
from .unotools import getProperty
from .unotools import getResourceLocation
from .contentcore import getSession
from .dbtools import getItemFromResult
from .dbtools import parseDateTime
from .dbtools import unparseDateTime
from .dbtools import RETRIEVED
from .dbtools import CREATED
from .dbtools import FOLDER
from .dbtools import FILE
from .dbtools import RENAMED
from .dbtools import REWRITED
from .dbtools import TRASHED


class IdentifierBase(object):
    pass


class ContentIdentifierBase(IdentifierBase,
                            unohelper.Base,
                            Initialization,
                            PropertySet,
                            XContentIdentifier,
                            XChild,
                            XInputStreamProvider,
                            XUpdatable,
                            XLinkUpdate,
                            XContentIdentifierFactory,
                            XInstanceProvider):
    def __init__(self, ctx, namedvalues):
        self.ctx = ctx
        self.User = None
        self.Uri = None
        self.initialize(namedvalues)
        self.IsNew = self.Uri.hasFragment()
        self._Error = None
        self.Size = 0
        self.MimeType = None
        self.Updated = False
        self.Id, self.Title, self.Url = self._parseUri() if self.User.IsValid else (None, None, None)
        self.Session = getSession(self.ctx, self.Uri.getScheme(), self.User.Name) if self.IsValid else None
        self.RETRIEVED = RETRIEVED
        self.CREATED = CREATED
        self.FOLDER = FOLDER
        self.FILE = FILE
        self.RENAMED = RENAMED
        self.REWRITED = REWRITED
        self.TRASHED = TRASHED

    @property
    def IsRoot(self):
        return self.Id == self.User.RootId
    @property
    def IsValid(self):
        return all((self.Id, self._Error is None))
    @property
    def BaseURL(self):
        return self.Url if self.IsRoot else '%s/%s' % (self.Url, self.Id)
    @property
    def SourceURL(self):
        return getResourceLocation(self.ctx, self.getPlugin(), self.getContentProviderScheme())
    @property
    def Error(self):
        return self._Error if self.User.Error is None else self.User.Error
    @property
    def Properties(self):
        raise NotImplementedError

    def getPlugin(self):
        raise NotImplementedError
    def getFolder(self):
        raise NotImplementedError
    def getLink(self):
        raise NotImplementedError
    def getDocument(self):
        raise NotImplementedError
    def updateChildren(self, session):
        raise NotImplementedError
    def getNewIdentifier(self):
        raise NotImplementedError
    def getItem(self, session):
        raise NotImplementedError
    def selectItem(self):
        raise NotImplementedError
    def insertJsonItem(self, data):
        raise NotImplementedError
    def isIdentifier(self, title):
        raise NotImplementedError
    def selectChildId(self, parent, title):
        raise NotImplementedError
    def unquote(self, text):
        raise NotImplementedError
    def mergeJsonItemCall(self):
        raise NotImplementedError
    def mergeJsonItem(self, merge, item, index):
        raise NotImplementedError
    def getItemToSync(self, mode):
        raise NotImplementedError
    def syncItem(self, session, item):
        raise NotImplementedError
    def updateSync(self, id, mode):
        result = 0
        if id is not None:
            update = self.User.Connection.prepareCall('CALL "updateSync"(?, ?, ?, ?)')
            update.setString(1, self.User.Id)
            update.setString(2, id)
            update.setLong(3, mode)
            update.execute()
            result = update.getLong(4)
            update.close()
        return result != 0
    def getDateTimeParser(self):
        return parseDateTime
    def unparseDateTime(self, datetime=None):
        return unparseDateTime(datetime)
    def getInputStream(self, path, id):
        url = '%s/%s' % (path, id)
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def getItemFromResult(self, result, data=None, transform=None):
        return getItemFromResult(result, data, transform)

    def doSync(self, session):
        results = []
        path = self.SourceURL
        for item in self.getItemToSync(RETRIEVED):
            id = self.syncItem(session, path, item)
            results.append(self.updateSync(id, RETRIEVED))
            if id:
                print("items.doSync(): all -> Ok")
            else:
                print("items.doSync(): all -> Error")
        return all(results)

    # XInputStreamProvider
    def createInputStream(self):
        raise NotImplementedError

    # XUpdatable
    def update(self):
        self.Updated = True
        if self.User.Mode == ONLINE:
            with self.Session as s:
                self.Updated = self.doSync(s)

    # XLinkUpdate
    def updateLinks(self):
        self.Updated = False
        if self.User.Mode == ONLINE:
            with self.Session as s:
                self.Updated = self.updateChildren(s)

    # XContentIdentifierFactory
    def createContentIdentifier(self, title=''):
        id = self.getNewIdentifier(self.User.Connection, self.User.Id)
        title = title if title else id
        uri = getUri(self.ctx, '%s/%s#%s' % (self.BaseURL, title, id))
        identifier = createContentIdentifier(self.ctx, self.getPlugin(), self.User, uri)
        print("ContentIdentifier.createContentIdentifier %s" % identifier.getContentIdentifier())
        return identifier

    # XInstanceProvider
    def getInstance(self, mimetype):
        data = {'MimeType': mimetype}
        if not mimetype:
            item = self._getItem()
            if item is not None:
                data = item.get('Data', {})
        content = createContent(self.ctx, self, data, self.getPlugin(), self.getFolder(), self.getLink(), self.getDocument())
        if content is None:
            message = "ERROR: Can't handle mimetype: %s" % data.get('MimeType', 'application/octet-stream')
            self._Error = IllegalIdentifierException(message, self)
        return content

    # XContentIdentifier
    def getContentIdentifier(self):
        return self.Uri.getUriReference()
    def getContentProviderScheme(self):
        return self.Uri.getScheme()

    # XChild
    def getParent(self):
        uri = getUri(self.ctx, self.Url)
        return createContentIdentifier(self.ctx, self.getPlugin(), self.User, uri)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    def _parseUri(self):
        title, position, url = None, -1, None
        parentid, paths = self.User.RootId, []
        for i in range(self.Uri.getPathSegmentCount() -1, -1, -1):
            path = self.Uri.getPathSegment(i).strip()
            if path not in ('','.'):
                if title is None:
                    title = self._unquote(path)
                    position = i
                else:
                    parentid = path
                    break
        if title is None:
            id = self.User.RootId
        elif self.IsNew:
            id = self.Uri.getFragment()
        elif self.isIdentifier(title):
            print("ContentIdentifier._parseUri() isIdentifier: %s" % title)
            id = title
        else:
            id = self.selectChildId(parentid, title)
        for i in range(position):
            paths.append(self.Uri.getPathSegment(i).strip())
        if id is None:
            id = self._searchId(paths[::-1], title)
        if id is None:
            message = "ERROR: Can't retrieve Uri: %s" % self.Uri.getUriReference()
            print("ContentIdentifier._parseUri() Error: %s" % message)
            self._Error = IllegalIdentifierException(message, self)
        paths.insert(0, self.Uri.getAuthority())
        url = '%s://%s' % (self.Uri.getScheme(), '/'.join(paths))
        return id, title, url

    def _searchId(self, paths, title):
        # Needed for be able to create a folder in a just created folder...
        paths.append(self.User.RootId)
        for index, path in enumerate(paths):
            if self.isIdentifier(self.User.Connection, self.User.Id, path):
                id = path
                break
        for i in range(index -1, -1, -1):
            path = self._unquote(paths[i])
            id = self.selectChildId(id, path)
        id = self.selectChildId(id, title)
        return id

    def _unquote(self, text):
        # Needed for OpenOffice / LibreOffice compatibility
        if isinstance(text, str):
            text = self.unquote(text)
        else:
            text = self.unquote(text.encode('utf-8')).decode('utf-8')
        return text

    def _getItem(self):
        item = self.selectItem()
        if item is not None:
            return item
        if self.User.Mode == ONLINE:
            with self.Session as s:
                data = self.getItem(s)
            if data is not None:
                item = self.insertJsonItem(data)
            else:
                message = "ERROR: Can't retrieve Id from provider: %s" % self.Id
                self._Error = IllegalIdentifierException(message, self)
        else:
            message = "ERROR: Can't retrieve Content: %s Network is Offline" % self.Id
            self._Error = IllegalIdentifierException(message, self)
        return item

    def updateChildren(self, session):
        merge, index = self.mergeJsonItemCall()
        update = all(self.mergeJsonItem(merge, item, index) for item in ChildGenerator(session, self.Id))
        merge.close()
        return update

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['User'] = getProperty('User', 'com.sun.star.uno.XInterface', maybevoid | bound | readonly)
        properties['Uri'] = getProperty('Uri', 'com.sun.star.uri.XUriReference', bound | readonly)
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['IsRoot'] = getProperty('IsRoot', 'boolean', bound | readonly)
        properties['IsValid'] = getProperty('IsValid', 'boolean', bound | readonly)
        properties['IsNew'] = getProperty('IsNew', 'boolean', bound | readonly)
        properties['BaseURL'] = getProperty('BaseURL', 'string', bound | readonly)
        properties['SourceURL'] = getProperty('SourceURL', 'string', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', maybevoid | bound | readonly)
        properties['Updated'] = getProperty('Updated', 'boolean', bound | readonly)
        properties['Size'] = getProperty('Size', 'long', maybevoid | bound)
        properties['MimeType'] = getProperty('MimeType', 'string', maybevoid | bound)
        properties['Properties'] = getProperty('Properties', '[]string', bound | readonly)
        properties['Error'] = getProperty('Error', 'com.sun.star.ucb.IllegalIdentifierException', maybevoid | bound | readonly)
        return properties


class ChildGenerator():
    pass
