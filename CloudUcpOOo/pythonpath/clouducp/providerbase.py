#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from com.sun.star.ucb import XRestProvider

# oauth2 is only available after OAuth2OOo as been loaded...
try:
    from oauth2 import KeyMap
except ImportError:
    pass

from .unotools import getResourceLocation
from .configuration import g_oauth2

import datetime
import traceback


class ProviderObject(object):
    pass


class ProviderBase(ProviderObject,
                   unohelper.Base,
                   XServiceInfo,
                   XRestProvider):
    def __init__(self, ctx):
        self.ctx = ctx
        self.Request = self.ctx.ServiceManager.createInstanceWithContext(g_oauth2, self.ctx)
        self.Scheme = None
        self.Plugin = None
        self.Link = None
        self.Folder = None
        self.SourceURL = None
        self.SessionMode = OFFLINE
        self._Error = ''

    # Must be implemented properties
    @property
    def Host(self):
        raise NotImplementedError
    @property
    def BaseUrl(self):
        raise NotImplementedError
    @property
    def UploadUrl(self):
        raise NotImplementedError
    @property
    def Office(self):
        raise NotImplementedError
    @property
    def Document(self):
        raise NotImplementedError
    @property
    def Chunk(self):
        raise NotImplementedError
    @property
    def Buffer(self):
        raise NotImplementedError

    # Base properties
    @property
    def Error(self):
        return self.Request.Error if self.Request.Error else self._Error

    # Can be rewrited properties
    @property
    def GenerateIds(self):
        return False
    @property
    def IdentifierRange(self):
        return (0, 0)
    @property
    def TimeStampPattern(self):
        return '%Y-%m-%dT%H:%M:%SZ'

    # Must be implemented method
    def getRequestParameter(self, method, data):
        raise NotImplementedError

    def getUserId(self, item):
        raise NotImplementedError
    def getUserName(self, item):
        raise NotImplementedError
    def getUserDisplayName(self, item):
        raise NotImplementedError

    def getItemId(self, item):
        raise NotImplementedError
    def getItemName(self, item):
        raise NotImplementedError
    def getItemCreated(self, item, timestamp=None):
        raise NotImplementedError
    def getItemModified(self, item, timestamp=None):
        raise NotImplementedError
    def getItemMediaType(self, item):
        raise NotImplementedError
    def getItemSize(self, item):
        raise NotImplementedError
    def getItemTrashed(self, item):
        raise NotImplementedError
    def getItemCanAddChild(self, item):
        raise NotImplementedError
    def getItemCanRename(self, item):
        raise NotImplementedError
    def getItemIsReadOnly(self, item):
        raise NotImplementedError
    def getItemIsVersionable(self, item):
        raise NotImplementedError

    def getItemParent(self, item, rootid):
        raise NotImplementedError

    def getUploadParameter(self, item, new):
        raise NotImplementedError
    def getUpdateParameter(self, item, new, key):
        raise NotImplementedError

    # Base method
    def isOnLine(self):
        return self.SessionMode != OFFLINE
    def isOffLine(self):
        return self.SessionMode != ONLINE

    def initialize(self, scheme, plugin, link, folder):
        self.Request.initializeSession(scheme)
        self.Scheme = scheme
        self.Plugin = plugin
        self.Link = link
        self.Folder = folder
        self.SourceURL = getResourceLocation(self.ctx, plugin, scheme)
        self.SessionMode = self.Request.getSessionMode(self.Host)

    def initializeUser(self, name):
        self.SessionMode = self.Request.getSessionMode(self.Host)
        if self.isOnLine():
            return self.Request.initializeUser(name)
        return True

    # Can be rewrited method
    def isFolder(self, contenttype):
        return contenttype == self.Folder
    def isLink(self, contenttype):
        return contenttype == self.Link
    def isDocument(self, contenttype):
        return not (self.isFolder(contenttype) or self.isLink(contenttype))

    def getRootId(self, item):
        return self.getItemId(item)
    def getRootName(self, item):
        return self.getItemName(item)
    def getRootCreated(self, item, timestamp=None):
        return self.getItemCreated(item, timestamp)
    def getRootModified(self, item, timestamp=None):
        return self.getItemModified(item, timestamp)
    def getRootMediaType(self, item):
        return self.getItemMediaType(item)
    def getRootSize(self, item):
        return self.getItemSize(item)
    def getRootTrashed(self, item):
        return self.getItemTrashed(item)
    def getRootCanAddChild(self, item):
        return self.getItemCanAddChild(item)
    def getRootCanRename(self, item):
        return self.getItemCanRename(item)
    def getRootIsReadOnly(self, item):
        return self.getItemIsReadOnly(item)
    def getRootIsVersionable(self, item):
        return self.getItemIsVersionable(item)

    def getResponseId(self, response, item):
        id = self.getItemId(response)
        if not id:
            id = self.getItemId(item)
        return id
    def getResponseName(self, response, item):
        name = self.getItemName(response)
        if not name:
            name = self.getItemName(item)
        return name
    def getTimeStamp(self):
        return datetime.datetime.now().strftime(self.TimeStampPattern)
    def transform(self, name, value):
        return value

    def getIdentifier(self, user):
        parameter = self.getRequestParameter('getNewIdentifier', user)
        return self.Request.getEnumerator(parameter)
    def getUser(self, name):
        data = KeyMap()
        data.insertValue('Id', name)
        parameter = self.getRequestParameter('getUser', data)
        return self.Request.execute(parameter)
    def getRoot(self, user):
        parameter = self.getRequestParameter('getRoot', user)
        return self.Request.execute(parameter)
    def getItem(self, user, identifier):
        parameter = self.getRequestParameter('getItem', identifier)
        return self.Request.execute(parameter)

    def getDocumentContent(self, content):
        print("ProviderBase.getDocumentContent() 1")
        parameter = self.getRequestParameter('getDocumentContent', content)
        return self.Request.getInputStream(parameter, self.Chunk, self.Buffer)
    def getFolderContent(self, content):
        print("ProviderBase.getFolderContent() 1")
        parameter = self.getRequestParameter('getFolderContent', content)
        return self.Request.getEnumerator(parameter)

    def updateContent(self, parameter):
        print("Provider.updateContent() 1")
        return self.Request.execute(parameter)

    def getUploader(self, datasource):
        return self.Request.getUploader(datasource)

    def _getKeyMapFromResult(self, result, keymap, transform=False):
        #print("DataSource._getKetMapFromResult() %s" % result.MetaData.ColumnCount)
        for i in range(1, result.MetaData.ColumnCount +1):
            dbtype = result.MetaData.getColumnTypeName(i)
            name = result.MetaData.getColumnName(i)
            if dbtype == 'VARCHAR':
                value = result.getString(i)
            elif dbtype == 'TIMESTAMP':
                value = result.getTimestamp(i)
            elif dbtype == 'BOOLEAN':
                value = result.getBoolean(i)
            elif dbtype == 'BIGINT' or dbtype == 'SMALLINT':
                value = result.getLong(i)
            else:
                #print("DataSource._getKetMapFromResult() %s - %s" % (dbtype, name))
                continue
            #print("DataSource._getKetMapFromResult() %s - %s - %s" % (i, name, value))
            if result.wasNull():
                value = None
            if transform:
                value = self.transform(name, value)
            keymap.insertValue(name, value)
        return keymap
