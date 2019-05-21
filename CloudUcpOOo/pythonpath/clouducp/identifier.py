#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier
from com.sun.star.ucb import XRestIdentifier
from com.sun.star.beans.PropertyAttribute import BOUND
from com.sun.star.beans.PropertyAttribute import CONSTRAINED
from com.sun.star.beans.PropertyAttribute import READONLY
from com.sun.star.beans.PropertyAttribute import TRANSIENT
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from .keymap import KeyMap
from .contenttools import getUri
from .unotools import getProperty
from .unotools import getResourceLocation
from .dbtools import parseDateTime

import traceback


class Identifier(unohelper.Base,
                 XContentIdentifier,
                 XRestIdentifier,
                 XChild):
    def __init__(self, ctx, user, uri, contenttype=None):
        self.ctx = ctx
        self.User = user
        self._Uri = uri
        self._ContentType = contenttype
        isnew = contenttype is not None
        self._Error = ''
        if self.User.IsValid:
            self.MetaData, self._Error = self.User.initializeIdentifier(uri, isnew, self._Error)
        else:
            self.MetaData = KeyMap()

    def initializeContent(self):
        print("Identifier.initializeContent()")
        if self.IsNew:
            isfolder = self.User.DataSource.Provider.isFolder(self._ContentType)
            isdocument = self.User.DataSource.Provider.isDocument(self._ContentType)
            item = KeyMap(**{'Id': id})
            item.insertValue('ContentType', self._ContentType)
            item.insertValue('DateCreated', parseDateTime())
            item.insertValue('IsFolder', isfolder)
            item.insertValue('IsDocument', isdocument)
            item.insertValue('CanAddChild', True)
            item.insertValue('CanRename', True)
            item.insertValue('IsVersionable', False)
            item.insertValue('Loaded', True)
            item.insertValue('Trashed', False)
        else:
            item = self.User.getItem(self.MetaData)
        item.insertValue('BaseURI', self.MetaData.getValue('BaseURI'))
        return item

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('Id', None)
    @property
    def IsRoot(self):
        return self.MetaData.getDefaultValue('IsRoot', False)
    @property
    def IsValid(self):
        return all((self.Id, not self.Error))
    @property
    def IsNew(self):
        return self.MetaData.getValue('IsNew')
    @property
    def BaseURI(self):
        return self.MetaData.getValue('BaseURI')
    @property
    def BaseURL(self):
        return self.BaseURI if self.IsRoot else '%s/%s' % (self.BaseURI, self.Id)
    @property
    def Error(self):
        return self.User.Error if self.User.Error else self._Error


    def insertNewDocument(self, content):
        parentid = self.getParent().Id
        return self.User.insertNewDocument(self.Id, parentid, content)
    def insertNewFolder(self, content):
        parentid = self.getParent().Id
        return self.User.insertNewFolder(self.Id, parentid, content)

    def isChildId(self, title):
        return self.User.isChildId(self.Id, title)
    def selectChildId(self, title):
        return self.User.selectChildId(self.Id, title)
    def countChildTitle(self, title):
        return self.User.countChildTitle(self.Id, title)

    def updateTrashed(self, value, default):
        return self.User.updateTrashed(self.Id, value, default)
    def updateTitle(self, value, default):
        return self.User.updateTitle(self.Id, value, default)
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

    def getInputStream(self, path, id):
        url = '%s/%s' % (path, id)
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    # XRestIdentifier
    def createNewIdentifier(self, title, contenttype):
        url = '%s/%s' % (self.BaseURL, title)
        print("Identifier.createNewIdentifier() 1 %s" % url)
        uri = getUri(self.ctx, url)
        return Identifier(self.ctx, self.User, uri, contenttype)

    def getDocumentContent(self, sf, content, size):
        print("Identifier.getDocumentContent() 1")
        size = 0
        url = '%s/%s' % (self.User.DataSource.Provider.SourceURL, self.Id)
        print("Identifier.getDocumentContent() 2")
        if content.getValue('Loaded') == OFFLINE and sf.exists(url):
            size = sf.getSize(url)
            return url, size
        print("Identifier.getDocumentContent() 3")
        stream = self.User.DataSource.Provider.getDocumentContent(content)
        if stream:
            try:
                sf.writeFile(url, stream)
            except Exception as e:
                print("Identifier.getDocumentContent().Error: %s - %s" % (e, traceback.print_exc()))
                pass
            else:
                size = sf.getSize(url)
                loaded = self.User.updateLoaded(self.Id, OFFLINE, ONLINE)
                content.insertValue('Loaded', loaded)
            finally:
                stream.closeInput()
        return url, size

    def getFolderContent(self, content, index):
        select, index, updated = self.User.getFolderContent(self.MetaData, content, index, False)
        if updated:
            loaded = self.User.updateLoaded(self.Id, OFFLINE, ONLINE)
            content.insertValue('Loaded', loaded)
        return select, index

    # XContentIdentifier
    def getContentIdentifier(self):
        url = self._Uri.getUriReference()
        print("Identifier.getContentIdentifier(): %s" % url)
        return url
    def getContentProviderScheme(self):
        return self.User.DataSource.Provider.Scheme

    # XChild
    def getParent(self):
        uri = getUri(self.ctx, self.BaseURI)
        return Identifier(self.ctx, self.User, uri)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    def _getContentData(self):
        data = KeyMap()
        for name in ('Title', 'DateCreated', 'DateModified', 'MediaType', 'Size',
                     'Trashed','CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable'):
            data.insertValue(name, getattr(self, name))
        data.insertValue('Parent', self.getParent().Id)
        print("Identifier._getContentData() %s" % self.getParent().Id)
        return data

    def _getUrl(self, url):
        if self.IsFolder and not url.endswith('/'):
            url += '/'
        return url
