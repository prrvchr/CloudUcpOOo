#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.io import XStreamListener
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RETRIEVED
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from com.sun.star.ucb import XRestProvider

from .request import Request
from .keymap import KeyMap
from .unotools import getResourceLocation

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
        self.Request = Request(ctx)
        self.Scheme = None
        self.Plugin = None
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
    def Folder(self):
        raise NotImplementedError
    @property
    def Link(self):
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

    def initialize(self, scheme, plugin):
        self.Scheme = scheme
        self.Plugin = plugin
        self.SourceURL = getResourceLocation(self.ctx, plugin, scheme)

    def initializeSession(self, name):
        self.SessionMode = self.Request.getSessionMode(self.Host)
        if self.isOnLine():
            self.Request.initializeSession(self.Scheme, name)

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
        data = KeyMap(**{'Id': name})
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

    def insertContent(self, parameter):
        print("Provider.updateContent() 1")
        return self.Request.execute(parameter)

    def updateContent(self, parameter):
        print("Provider.updateContent() 1")
        return self.Request.execute(parameter)

    def uploadContent(self, connection, parameter, item, input, size):
        print("Provider.uploadContent() 1")
        #response = uno.createUnoStruct('com.sun.star.beans.Optional<com.sun.star.ucb.XRestKeyMap>')
        print("Provider.uploadContent() 2")
        output, response = self.Request.getOutputStream(parameter, size, self.Chunk, None)
        print("Provider.uploadContent() 3")
        listener = StreamListener(connection, self, item, response)
        print("Provider.uploadContent() 4")
        pump = self.ctx.ServiceManager.createInstance('com.sun.star.io.Pump')
        pump.setInputStream(input)
        pump.setOutputStream(output)
        pump.addListener(listener)
        pump.start()


class StreamListener(unohelper.Base,
                     XStreamListener):
    def __init__(self, connection, provider, item, response):
        self.connection = connection
        self.provider = provider
        self.item = item
        self.response = response

    # XStreamListener
    def started(self):
        print("StreamListener.started() *****************************************************")
    def closed(self):
        print("StreamListener.closed() 1")
        if self.response.IsPresent:
            print("StreamListener.closed() 2")
            call = self.connection.prepareCall('CALL "updateSync"(?, ?, ?, ?, ?, ?, ?)')
            call.setString(1, self.item.getValue('UserId'))
            call.setLong(2, SYNC_RETRIEVED)
            print("StreamListener.closed() 3")
            call.setString(3, self.provider.getItemId(self.item))
            call.setString(4, self.provider.getResponseId(self.response.Value, self.item))
            print("StreamListener.closed() 4")
            call.setString(5, self.provider.getItemName(self.item))
            call.setString(6, self.provider.getResponseName(self.response.Value, self.item))
            print("StreamListener.closed() 5")
            call.execute()
            result = call.getLong(7)
            call.close()
            print("StreamListener.closed() *****************************************************")
        else:
            print("StreamListener.closed() ERROR * ERROR * ERROR * ERROR * ERROR * ERROR * ERROR")
    def terminated(self):
        pass
    def error(self, error):
        print("StreamListener.error() *****************************************************")
    def disposing(self, event):
        pass
