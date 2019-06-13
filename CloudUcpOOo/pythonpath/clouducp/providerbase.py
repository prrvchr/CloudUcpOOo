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

from .dbtools import parseDateTime
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
    def getItemTitle(self, item):
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
    def parseDateTime(self, timestamp, format='%Y-%m-%dT%H:%M:%S.%fZ'):
        return parseDateTime(timestamp, format)
    def isOnLine(self):
        return self.SessionMode != OFFLINE
    def isOffLine(self):
        return self.SessionMode != ONLINE

    def initialize(self, scheme, plugin, folder, link):
        self.Request.initializeSession(scheme)
        self.Scheme = scheme
        self.Plugin = plugin
        self.Folder = folder
        self.Link = link
        self.SourceURL = getResourceLocation(self.ctx, plugin, scheme)
        self.SessionMode = self.Request.getSessionMode(self.Host)

    def initializeUser(self, name):
        print("ProviderBase.initializeUser() 1")
        self.SessionMode = self.Request.getSessionMode(self.Host)
        if self.isOnLine():
            print("ProviderBase.initializeUser() 2")
            return self.Request.initializeUser(name)
        print("ProviderBase.initializeUser() FIN")
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
    def getRootTitle(self, item):
        return self.getItemTitle(item)
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

    def getResponseId(self, response, default):
        id = self.getItemId(response)
        if not id:
            id = default
        return id
    def getResponseTitle(self, response, default):
        title = self.getItemTitle(response)
        if not title:
            title = default
        return title
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
        print("Provider.getUploader() 1")
        return self.Request.getUploader(datasource)

    def getUploadParameter(self, identifier, new):
        print("Provider.getUploadParameter() 1")
        if new:
            parameter = self.getRequestParameter('getNewUploadLocation', identifier)
        else:
            parameter = self.getRequestParameter('getUploadLocation', identifier)
        print("Provider.getUploadParameter() 2")
        response = self.Request.execute(parameter)
        if response.IsPresent:
            print("Provider.getUploadParameter() 3")
            return self.getRequestParameter('getUploadStream', response.Value)
        return None

    def getUpdateParameter(self, identifier, new, key):
        if new:
            parameter = self.getRequestParameter('insertContent', identifier)
        elif key == 'Title':
            parameter = self.getRequestParameter('updateTitle', identifier)
        elif key == 'Trashed':
            parameter = self.getRequestParameter('updateTrashed', identifier)
        return parameter
