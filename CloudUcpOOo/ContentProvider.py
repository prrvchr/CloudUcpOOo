#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.frame import XTerminateListener
from com.sun.star.lang import XServiceInfo
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.ucb import XContentIdentifierFactory
from com.sun.star.ucb import XContentProvider
from com.sun.star.ucb import XParameterizedContentProvider
from com.sun.star.ucb import XContentProvider
from com.sun.star.ucb import IllegalIdentifierException

from com.sun.star.ucb import XRestContentProvider

from clouducp import DataSource
from clouducp import InteractionRequestParameters
from clouducp import getInteractionHandler
from clouducp import getLogger
from clouducp import getUcb
from clouducp import getUri

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.CloudUcpOOo.ContentProvider'


class ContentProvider(unohelper.Base,
                      XServiceInfo,
                      XContentIdentifierFactory,
                      XContentProvider,
                      XParameterizedContentProvider,
                      XTerminateListener,
                      XRestContentProvider):
    def __init__(self, ctx):
        print("ContentProvider.__init__()***********************")
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self.DataSource = None
        self.Logger = getLogger(self.ctx)
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "__init__()", msg)

    def __del__(self):
        print("ContentProvider.__del__()***********************")

    # XParameterizedContentProvider
    def registerInstance(self, template, plugin, replace):
        print("ContentProvider.registerInstance() 1")
        datasource = DataSource(self.ctx, template, plugin, False)
        print("ContentProvider.registerInstance() 3")
        if not datasource.IsValid:
            self.Logger.logp(SEVERE, "ContentProvider", "registerInstance()", datasource.Error)
            print("ContentProvider.registerInstance() DataBase Connection ERROR")
            return None
        print("ContentProvider.registerInstance() 4")
        self.DataSource = datasource
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        provider = getUcb(self.ctx).registerContentProvider(self, template, replace)
        print("ContentProvider.registerInstance() 5")
        return provider
    def deregisterInstance(self, template, argument):
        getUcb(self.ctx).deregisterContentProvider(self, template)

    # XTerminateListener
    def queryTermination(self, event):
        pass
    def notifyTermination(self, event):
        if self.DataSource.shutdownConnection(False):
            level, msg = INFO, "Shutdown database ... closing connection ... Done"
        else:
            level, msg = SEVERE, "Shutdown database ... connection alredy closed !!!"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)

    # XContentIdentifierFactory
    def createContentIdentifier(self, url):
        try:
            print("ContentProvider.createContentIdentifier() 1 %s" % url)
            msg = "Identifier: %s ..." % url
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
            url = self._getUrl(url)
            uri = getUri(self.ctx, url)
            name = self._getUserName(uri)
            user = self.DataSource.getUser(name)
            print("ContentProvider.createContentIdentifier() 2 %s" % url)
            identifier = user.getIdentifier(uri)
            msg = "Identifier: %s ... Done" % identifier.getContentIdentifier()
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
            return identifier
        except Exception as e:
            print("ContentProvider.createContentIdentifier().Error: %s - %s" % \
                                                                (e, traceback.print_exc()))

    # XContentProvider
    def queryContent(self, identifier):
        print("ContentProvider.queryContent() 1 %s - %s\n%s" % \
            (identifier.IsValid, identifier.User.IsValid, identifier.getContentIdentifier()))
        msg = "Identifier: %s... " % identifier.getContentIdentifier()
        if not identifier.IsValid:
            self.Logger.logp(INFO, "ContentProvider", "queryContent()", "%s - %s" % \
                                                                (msg, identifier.Error))
            print("ContentProvider.queryContent() 3 %s - %s" % (msg, identifier.Error))
            raise IllegalIdentifierException(identifier.Error, self)
        content = identifier.getContent()
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
        print("ContentProvider.queryContent() 4 %s" % identifier.getContentIdentifier())
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
        msg += " compare is: %s... Done" % compare
        print("ContentProvider.compareContentIds() %s" % msg)
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
        if uri.hasAuthority() and uri.getAuthority() != '':
            name = uri.getAuthority()
        else:
            name = self._getUserNameFromHandler()
        return name

    def _getUserNameFromHandler(self):
        result = uno.createUnoStruct('com.sun.star.beans.Optional<string>')
        message = "Authentication is needed!!!"
        handler = getInteractionHandler(self.ctx, message)
        request = InteractionRequestParameters(self, self.Connection, message, result)
        if handler.handleInteractionRequest(request):
            if result.IsPresent:
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
