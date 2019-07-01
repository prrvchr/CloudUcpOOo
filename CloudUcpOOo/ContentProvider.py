#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.util import XCloseListener
from com.sun.star.lang import XServiceInfo
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.ucb import XContentIdentifierFactory
from com.sun.star.ucb import XContentProvider
from com.sun.star.ucb import XParameterizedContentProvider
from com.sun.star.ucb import XContentProvider
from com.sun.star.ucb import IllegalIdentifierException

from com.sun.star.ucb import XRestContentProvider

from clouducp import g_identifier
from clouducp import DataSource
from clouducp import InteractionRequestParameters
from clouducp import getInteractionHandler
from clouducp import getLogger
from clouducp import isLoggerEnabled
from clouducp import getUcb
from clouducp import getUri

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.ContentProvider' % g_identifier


class ContentProvider(unohelper.Base,
                      XServiceInfo,
                      XContentIdentifierFactory,
                      XContentProvider,
                      XCloseListener,
                      XParameterizedContentProvider,
                      XRestContentProvider):
    def __init__(self, ctx):
        self.ctx = ctx
        self.Scheme = ''
        self.Plugin = ''
        self.DataSource = None
        self.Logger = getLogger(self.ctx) if isLoggerEnabled(self.ctx) else None
        self._defaultUser = None
        if self.Logger:
           msg = "ContentProvider loading ... Done"
           self.Logger.logp(INFO, "ContentProvider", "__init__()", msg)

    def __del__(self):
        if self.Logger:
           msg = "ContentProvider unloading ... Done"
           self.Logger.logp(INFO, "ContentProvider", "__del__()", msg)

    # XParameterizedContentProvider
    def registerInstance(self, scheme, plugin, replace):
        service = '%s.Provider' % plugin
        provider = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        datasource = DataSource(self.ctx, provider, scheme, plugin, self.Logger)
        if not datasource.IsValid:
            if self.Logger:
                self.Logger.logp(SEVERE, "ContentProvider", "registerInstance()", datasource.Error)
            return None
        self.Scheme = scheme
        self.Plugin = plugin
        datasource.Connection.Parent.DatabaseDocument.addCloseListener(self)
        self.DataSource = datasource
        if self.Logger:
            msg = "ContentProvider registerInstance: Scheme/Plugin: %s/%s ... Done"
            self.Logger.logp(INFO, "ContentProvider", "registerInstance()", msg % (scheme, plugin))
        return getUcb(self.ctx).registerContentProvider(self, scheme, replace)
    def deregisterInstance(self, scheme, argument):
        getUcb(self.ctx).deregisterContentProvider(self, scheme)
        if self.Logger:
            msg = "ContentProvider deregisterInstance: Scheme: %s ... Done"
            self.Logger.logp(INFO, "ContentProvider", "deregisterInstance()", msg % scheme)

    # XCloseListener
    def queryClosing(self, source, ownership):
        self.deregisterInstance(self.Scheme, self.Plugin)
        query = 'SHUTDOWN COMPACT;'
        statement = self.DataSource.Connection.createStatement()
        statement.execute(query)
        if self.Logger:
            msg = "ContentProvider queryClosing: Scheme: %s ... Done"
            self.Logger.logp(INFO, "ContentProvider", "queryClosing()", msg % self.Scheme)
    def notifyClosing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, url):
        if self.Logger:
            msg = "Identifier: %s ..." % url
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
        url = self._getUrl(url)
        uri = getUri(self.ctx, url)
        name = self._getUserName(uri)
        user = self.DataSource.getUser(name)
        identifier = user.getIdentifier(uri)
        if self.Logger:
           msg = "Identifier: %s ... Done" % identifier.getContentIdentifier()
           self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
        return identifier

    # XContentProvider
    def queryContent(self, identifier):
        url = identifier.getContentIdentifier()
        if not identifier.IsValid:
            if self.Logger:
                msg = "Identifier: %s ... Error: %s" % (url, identifier.Error)
                self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
            raise IllegalIdentifierException(identifier.Error, self)
        content = identifier.getContent()
        if self.Logger:
            msg = "Identitifer: %s ... Done" % url
            self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
        return content

    def compareContentIds(self, id1, id2):
        compare = -1
        identifier1 = id1.getContentIdentifier()
        identifier2 = id2.getContentIdentifier()
        msg = "Identifiers: %s - %s ..." % (identifier1, identifier2)
        if identifier1 == identifier2 and id1.User.Name == id2.User.Name:
            msg += " seem to be the same..."
            compare = 0
        elif not id1.IsValid and id2.IsValid:
            msg += " are not the same..."
            compare = -10
        elif id1.IsValid and not id2.IsValid:
            msg += " are not the same..."
            compare = 10
        if self.Logger:
            msg += " ... Done"
            self.Logger.logp(INFO, "ContentProvider", "compareContentIds()", msg)
        return compare

    def _getUrl(self, identifier):
        url = uno.createUnoStruct('com.sun.star.util.URL')
        url.Complete = identifier
        transformer = self.ctx.ServiceManager.createInstance('com.sun.star.util.URLTransformer')
        success, url = transformer.parseStrict(url)
        if success:
            identifier = transformer.getPresentation(url, True)
        return identifier

    def _getUserName(self, uri):
        if not uri.getPathSegmentCount():
            return ''
        if uri.hasAuthority() and uri.getAuthority() != '':
            name = uri.getAuthority()
            self._defaultUser = None
        elif self._defaultUser is not None:
            name = self._defaultUser
        else:
            name = self._getUserNameFromHandler()
        return name

    def _getUserNameFromHandler(self):
        result = uno.createUnoStruct('com.sun.star.beans.Optional<string>')
        message = "Authentication is needed!!!"
        handler = getInteractionHandler(self.ctx, message)
        request = InteractionRequestParameters(self, self.DataSource.Connection, message, result)
        if handler.handleInteractionRequest(request):
            if result.IsPresent:
                self._defaultUser = result.Value
                return result.Value
        return ''

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentProvider,
                                         g_ImplementationName,
                                        (g_ImplementationName, 'com.sun.star.ucb.ContentProvider'))
