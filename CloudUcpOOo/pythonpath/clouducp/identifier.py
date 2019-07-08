#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier
from com.sun.star.ucb import XRestIdentifier
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.beans.PropertyAttribute import BOUND
from com.sun.star.beans.PropertyAttribute import CONSTRAINED
from com.sun.star.beans.PropertyAttribute import READONLY
from com.sun.star.beans.PropertyAttribute import TRANSIENT
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from .content import Content

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
        level = INFO
        msg = "Identifier loading"
        self.ctx = ctx
        self.User = user
        self._Uri = uri.getUriReference()
        self._ContentType = contenttype
        isnew = contenttype is not None
        self._Error = ''
        if self.User.IsValid:
            self.MetaData, self._Error = self.User.initializeIdentifier(uri, isnew, self._Error)
            msg += " ... Done"
        else:
            self.MetaData = self.User.DataSource.Provider.Request.getKeyMap()
            level = SEVERE
            msg += " ... ERROR: %s" % self.Error
        self.Logger.logp(level, "Identifier", "__init__()", msg)

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
        return self.MetaData.getValue('BaseURL')
    @property
    def Logger(self):
        return self.User.DataSource.Logger
    @property
    def Error(self):
        return self.User.Error if self.User.Error else self._Error

    def getContent(self):
        print("Identifier.getContent()")
        if self.IsNew:
            timestamp = parseDateTime()
            isfolder = self.User.DataSource.Provider.isFolder(self._ContentType)
            isdocument = self.User.DataSource.Provider.isDocument(self._ContentType)
            data = self.User.DataSource.Provider.Request.getKeyMap()
            data.insertValue('Id', id)
            data.insertValue('ContentType', self._ContentType)
            data.insertValue('DateCreated', timestamp)
            data.insertValue('DateModified', timestamp)
            if isfolder:
                folder = self.User.DataSource.Provider.Folder
                data.insertValue('MediaType', folder)
            data.insertValue('Size', 0)
            data.insertValue('Trashed', False)
            data.insertValue('CanAddChild', True)
            data.insertValue('CanRename', True)
            data.insertValue('IsReadOnly', False)
            data.insertValue('IsVersionable', False)
            data.insertValue('Loaded', True)
            data.insertValue('IsFolder', isfolder)
            data.insertValue('IsDocument', isdocument)
        else:
            data = self.User.getItem(self.MetaData)
        data.insertValue('BaseURI', self.MetaData.getValue('BaseURI'))
        return Content(self.ctx, self, data)

    def setTitle(self, title, isfolder):
        id = self.Id if isfolder else title
        self._Uri = '%s/%s' % (self._Uri, id)
        self.MetaData.insertValue('BaseName', id)
        return title

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
        parentid = self.getParent().Id
        return self.User.updateTrashed(self.Id, parentid, value, default)
    def updateTitle(self, value, default):
        parentid = self.getParent().Id
        return self.User.updateTitle(self.Id, parentid, value, default)

    def getInputStream(self, path, id):
        url = '%s/%s' % (path, id)
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    # XRestIdentifier
    def createNewIdentifier(self, contenttype):
        url = self.BaseURL
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

    def getFolderContent(self, content):
        select, updated = self.User.getFolderContent(self.MetaData, content, False)
        if updated:
            msg = "updated: %s" % updated
            self.Logger.logp(INFO, "Identifier", "getFolderContent()", msg)
            loaded = self.User.updateLoaded(self.Id, OFFLINE, ONLINE)
            content.insertValue('Loaded', loaded)
        return select

    # XContentIdentifier
    def getContentIdentifier(self):
        url = self._Uri
        print("Identifier.getContentIdentifier(): %s" % url)
        return url
    def getContentProviderScheme(self):
        return self.User.DataSource.Provider.Scheme

    # XChild
    def getParent(self):
        url = '%s/' % self.BaseURI
        uri = getUri(self.ctx, url)
        return self.User.getIdentifier(uri)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)
