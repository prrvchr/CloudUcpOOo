#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener
from com.sun.star.lang import XServiceInfo
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.ucb import XContentIdentifierFactory
from com.sun.star.ucb import XContentProvider
from com.sun.star.ucb import XParameterizedContentProvider

from clouducp import InteractionRequestParameters
from clouducp import PropertySet
from clouducp import createContentIdentifier
from clouducp import createContentUser
from clouducp import getDbConnection
from clouducp import getInteractionHandler
from clouducp import getLogger
from clouducp import getProperty
from clouducp import getUcb
from clouducp import getUri
from clouducp import updateContent

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.CloudUcpOOo.ContentProvider'


class ContentProvider(unohelper.Base, XServiceInfo, XContentIdentifierFactory, PropertySet,
                      XContentProvider, XPropertiesChangeListener, XParameterizedContentProvider,
                      XTerminateListener):
    def __init__(self, ctx):
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self._Statement = None
        self.Plugin = None
        self.cachedUser = {}
        self.cachedIdentifier = {}
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "__init__()", msg)

    def __del__(self):
        print("ContentProvider.__del__()***********************")

    @property
    def Connection(self):
        return self._Statement.getConnection()

    # XParameterizedContentProvider
    def registerInstance(self, template, plugin, replace):
        print("ContentProvider.registerInstance() 1 %s - %s" % (template, plugin))
        # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
        self.Plugin = plugin
        self._Statement = getDbConnection(self.ctx, template, plugin, True).createStatement()
        print("ContentProvider.registerInstance() 2")
        provider = getUcb(self.ctx).registerContentProvider(self, template, replace)
        return provider
    def deregisterInstance(self, template, argument):
        getUcb(self.ctx).deregisterContentProvider(self, template)

    # XTerminateListener
    def queryTermination(self, event):
        pass
    def notifyTermination(self, event):
        if self._Statement and not self.Connection.isClosed():
            self._Statement.execute('SHUTDOWN;')
            #self._Statement.execute('SHUTDOWN COMPACT;')
            level, msg = INFO, "Shutdown database ... closing connection ... Done"
        else:
            level, msg = SEVERE, "Shutdown database ... connection alredy closed !!!"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            name = event.PropertyName
            msg = "Item inserted new Id: %s ..." % event.NewValue if name == 'Id' else \
                  "Item updated Property: %s ..." % name
            self.Logger.logp(INFO, "ContentProvider", "propertiesChange()", msg)
            if updateContent(self.ctx, event):
                level = INFO
                msg = "Item inserted new Id: %s ... Done" % event.OldValue if name == 'Id' else \
                      "Item updated Property: %s ... Done" % event.PropertyName
            else:
                level = SEVERE
                msg = "ERROR: Can't insert new Id: %s" % event.OldValue if name == 'Id' else \
                      "ERROR: Can't update Property: %s" % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
    def disposing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        try:
            print("ContentProvider.createContentIdentifier() 1 %s" % identifier)
            msg = "Identifier: %s ..." % identifier
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
            key = self._getIdentifierKey(identifier)
            if key in self.cachedIdentifier:
                contentidentifier = self.cachedIdentifier[key]
            else:
                contentidentifier = self._getCachedIdentifier(identifier, key)
            msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
            print("ContentProvider.createContentIdentifier() 2 %s" % identifier)
            return contentidentifier
        except Exception as e:
            print("ContentProvider.createContentIdentifier().Error: %s - %s" % (e, traceback.print_exc()))

    # XContentProvider
    def queryContent(self, identifier):
        content = None
        print("ContentProvider.queryContent() 1 %s" % identifier.getContentIdentifier())
        msg = "Identifier: %s..." % identifier.getContentIdentifier()
        if not identifier.IsValid:
            self.Logger.logp(SEVERE, "ContentProvider", "queryContent()", "%s - %s" % (msg, identifier.Error.Message))
            print("ContentProvider.queryContent() %s - %s" % (msg, identifier.Error.Message))
            raise identifier.Error
        key = self._getIdentifierKey(identifier.getContentIdentifier())
        if key in self.cachedContent:
            content = self.cachedContent[key]
        else:
            content = self._getCachedContent(identifier, key)
        if not identifier.IsValid:
            self.Logger.logp(SEVERE, "ContentProvider", "queryContent()", "%s - %s" % (msg, identifier.Error.Message))
            print("ContentProvider.queryContent() %s - %s" % (msg, identifier.Error.Message))
            raise identifier.Error
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
        print("ContentProvider.queryContent() 2 %s" % identifier.getContentIdentifier())
        return content
    def compareContentIds(self, identifier1, identifier2):
        compare = 1
        print("ContentProvider.compareContentIds() %s - %s" % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier()))
        msg = "Identifiers: %s - %s ..." % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier())
        id1 = self._getIdentifierKey(identifier1.getContentIdentifier())
        id2 = self._getIdentifierKey(identifier2.getContentIdentifier())
        if id1 == id2 and identifier1.User.Name == identifier2.User.Name:
            msg += " seem to be the same..."
            compare = 0
        elif identifier1.Id is None and identifier2.Id is not None:
            msg += " are not the same..."
            compare = -10
        elif identifier1.Id is not None and identifier2.Id is None:
            msg += " are not the same..."
            compare = 10
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "compareContentIds()", msg)
        return compare

    def _getCachedIdentifier(self, identifier, key):
        uri = getUri(self.ctx, identifier)
        user = self._getUser(uri)
        contentidentifier = createContentIdentifier(self.ctx, self.Plugin, user, uri)
        if contentidentifier.IsValid:
            print("ContentProvider._getIdentifier(): *****************************")
            self.cachedIdentifier[key] = contentidentifier
        return contentidentifier

    def _getUser(self, uri):
        if uri.hasAuthority() and uri.getAuthority() != '':
            username = uri.getAuthority()
        else:
            username = self._getUserNameFromHandler()
        if username in self.cachedUser:
            user = self.cachedUser[username]
        else:
            user = self._getCachedUser(uri, username)
        return user

    def _getUserNameFromHandler(self):
        result = {}
        message = "Authentication is needed!!!"
        handler = getInteractionHandler(self.ctx, message)
        request = InteractionRequestParameters(self, self.Connection, message, result)
        if handler.handleInteractionRequest(request):
            if result.get('Retrieved', False):
                return result.get('UserName')
        return None

    def _getCachedUser(self, uri, username):
        user = createContentUser(self.ctx, self.Plugin, uri.getScheme(), self.Connection, username)
        if user.IsValid:
            print("ContentProvider._setUser(): *****************************")
            self.cachedUser[username] = user
        return user

    def _getCachedContent(self, identifier, key):
        content = identifier.getInstance('')
        if identifier.IsValid:
            print("ContentProvider._getContent(): **************************")
            self.cachedContent[key] = content
            content.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), self)
        return content

    def _getIdentifierKey(self, uri):
        while uri.endswith(('/','..','.')):
            uri = uri[:-1]
        return uri

    # PropertySet
    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | bound| readonly)
        properties['Plugin'] = getProperty('Plugin', 'string', maybevoid | bound | readonly)
        return properties

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentProvider,                                                    # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.ContentProvider'))          # List of implemented services
