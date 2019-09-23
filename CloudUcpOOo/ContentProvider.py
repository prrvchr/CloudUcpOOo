#!
# -*- coding: utf_8 -*-
import traceback

try:
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

    from clouducp import getLogger
    from clouducp import isLoggerEnabled

    from clouducp import DataSource
    from clouducp import User
    from clouducp import Identifier

except Exception as e:
    print("clouducp.__init__() ERROR: %s - %s" % (e, traceback.print_exc()))


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
        self._defaultUser = ''
        self.Logger = getLogger(self.ctx)
        msg = "ContentProvider: %s loading ... Done" % g_identifier
        self.Logger.logp(INFO, 'ContentProvider', '__init__()', msg)

    def __del__(self):
       msg = "ContentProvider; %s unloading ... Done" % g_identifier
       self.Logger.logp(INFO, "ContentProvider", "__del__()", msg)

    # XParameterizedContentProvider
    def registerInstance(self, scheme, plugin, replace):
        msg = "ContentProvider registerInstance: Scheme/Plugin: %s/%s ... Started"
        self.Logger.logp(INFO, "ContentProvider", "registerInstance()", msg % (scheme, plugin))
        try:
            datasource = DataSource(self.ctx, scheme, plugin)
        except Exception as e:
            msg = "ContentProvider registerInstance: Error: %s - %s" % (e, traceback.print_exc())
            self.Logger.logp(SEVERE, "ContentProvider", "registerInstance()", msg)
            return None
        if not datasource.IsValid:
            self.Logger.logp(SEVERE, "ContentProvider", "registerInstance()", datasource.Error)
            return None
        self.Scheme = scheme
        self.Plugin = plugin
        msg = "ContentProvider registerInstance: addCloseListener ... Done"
        self.Logger.logp(INFO, "ContentProvider", "registerInstance()", msg)
        datasource.Connection.Parent.DatabaseDocument.addCloseListener(self)
        self.DataSource = datasource
        msg = "ContentProvider registerInstance: Scheme/Plugin: %s/%s ... Done"
        self.Logger.logp(INFO, "ContentProvider", "registerInstance()", msg % (scheme, plugin))
        return self
    def deregisterInstance(self, scheme, argument):
        msg = "ContentProvider deregisterInstance: Scheme: %s ... Done"
        self.Logger.logp(INFO, "ContentProvider", "deregisterInstance()", msg % scheme)

    # XCloseListener
    def queryClosing(self, source, ownership):
        self.deregisterInstance(self.Scheme, self.Plugin)
        query = 'SHUTDOWN COMPACT;'
        statement = self.DataSource.Connection.createStatement()
        statement.execute(query)
        msg = "ContentProvider queryClosing: Scheme: %s ... Done"
        self.Logger.logp(INFO, "ContentProvider", "queryClosing()", msg % self.Scheme)
    def notifyClosing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, url):
        try:
            msg = "Identifier: %s ... " % url
            identifier = Identifier(self.ctx, self.DataSource, url)
            msg += "Done"
            self.Logger.logp(INFO, "ContentProvider", "createContentIdentifier()", msg)
            return identifier
        except Exception as e:
            msg += "Error: %s - %s" % (e, traceback.print_exc())
            self.Logger.logp(SEVERE, "ContentProvider", "createContentIdentifier()", msg)

    # XContentProvider
    def queryContent(self, identifier):
        url = identifier.getContentIdentifier()
        print("ContentProvider.queryContent() %s" % url)
        if not identifier.IsInitialized:
            if not identifier.initialize(self._defaultUser):
                msg = "Identifier: %s ... Error: %s" % (url, identifier.Error)
                print("ContentProvider.queryContent() %s" % msg)
                self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
                raise IllegalIdentifierException(identifier.Error, self)
        self._defaultUser = identifier.User.Name
        content = identifier.getContent()
        msg = "Identitifer: %s ... Done" % url
        self.Logger.logp(INFO, "ContentProvider", "queryContent()", msg)
        return content

    def compareContentIds(self, id1, id2):
        print("ContentProvider.compareContentIds() 1")
        try:
            init1 = True
            init2 = True
            compare = -1
            identifier1 = id1.getContentIdentifier()
            identifier2 = id2.getContentIdentifier()
            msg = "Identifiers: %s - %s ..." % (identifier1, identifier2)
            if not id1.IsInitialized:
                init1 = id1.initialize(self._defaultUser)
            if not id2.IsInitialized:
                init2 = id2.initialize(self._defaultUser)
            if not init1:
                compare = -10
            elif not init2:
                compare = 10
            elif identifier1 == identifier2 and id1.User.Name == id2.User.Name:
                msg += " seem to be the same..."
                compare = 0
            msg += " ... Done"
            self.Logger.logp(INFO, "ContentProvider", "compareContentIds()", msg)
            return compare
        except Exception as e:
            print("ContentProvider.compareContentIds() Error: %s - %s" % (e, traceback.print_exc()))

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
