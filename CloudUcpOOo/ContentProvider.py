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
                      XCloseListener,
                      XParameterizedContentProvider,
                      XRestContentProvider):
    def __init__(self, ctx):
        print("ContentProvider.__init__()***********************")
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self.Scheme = ''
        self.Plugin = ''
        self.DataSource = None
        self.Logger = getLogger(self.ctx)
        self._defaultUser = None
        msg += " Done"
        self.Logger.logp(INFO, "ContentProvider", "__init__()", msg)

    def __del__(self):
        print("ContentProvider.__del__()***********************")

    # XParameterizedContentProvider
    def registerInstance(self, template, plugin, replace):
        print("ContentProvider.registerInstance() 1")
        datasource = DataSource(self.ctx, template, plugin)
        print("ContentProvider.registerInstance() 3")
        if not datasource.IsValid:
            e = datasource.Error
            self.Logger.logp(SEVERE, "ContentProvider", "registerInstance()", e)
            print("ContentProvider.registerInstance() DataBase Connection ERROR: %s" % e)
            return None
        print("ContentProvider.registerInstance() 4")
        self.Scheme = template
        self.Plugin = plugin
        datasource.Connection.Parent.DatabaseDocument.addCloseListener(self)
        self.DataSource = datasource
        provider = getUcb(self.ctx).registerContentProvider(self, template, replace)
        print("ContentProvider.registerInstance() FIN")
        return provider
    def deregisterInstance(self, template, argument):
        print("ContentProvider.deregisterInstance() 1")
        getUcb(self.ctx).deregisterContentProvider(self, template)
        print("ContentProvider.deregisterInstance() FIN")

    # XCloseListener
    def queryClosing(self, source, ownership):
        try:
            print("ContentProvider.queryClosing() 1 %s" % ownership)
            self.deregisterInstance(self.Scheme, self.Plugin)
            print("ContentProvider.queryClosing() 2")
            query = 'SHUTDOWN COMPACT;'
            statement = self.DataSource.Connection.createStatement()
            statement.execute(query)
            print("ContentProvider.queryClosing() FIN")
        except Exception as e:
            print("ContentProvider.queryClosing().Error: %s - %s" % (e, traceback.print_exc()))
    def notifyClosing(self, source):
        print("ContentProvider.notifyClosing() FIN")

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
        if not uri.getPathSegmentCount():
            print("ContentProvider._getUserName() Not Complete ********")
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
                print("ContentProvider._getUserNameFromHandler() %s" % result.Value)
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
