#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from clouducp import g_identifier
from clouducp import getStringResource
from clouducp import getUcb
from clouducp import getUcp
from clouducp import getLogger

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.OptionsDialog' % g_identifier


class OptionsDialog(unohelper.Base,
                    XServiceInfo,
                    XContainerWindowEventHandler):
    def __init__(self, ctx):
        msg = "OptionsDialog for Plugin: %s loading ... " % g_identifier
        self.ctx = ctx
        self.stringResource = getStringResource(self.ctx, g_identifier, 'CloudUcpOOo', 'OptionsDialog')
        self.Logger = getLogger(self.ctx)
        msg += "Done"
        self.Logger.logp(INFO, 'OptionsDialog', '__init__()', msg)

    # XContainerWindowEventHandler
    def callHandlerMethod(self, dialog, event, method):
        handled = False
        if method == 'external_event':
            if event == 'ok':
                self._saveSetting(dialog)
                handled = True
            elif event == 'back':
                self._loadSetting(dialog)
                handled = True
            elif event == 'initialize':
                self._loadSetting(dialog)
                handled = True
        elif method == 'Changed':
            self._doChanged(dialog, event.Source)
            handled = True
        elif method == 'LoadUcp':
            self._doLoadUcp(dialog)
            handled = True
        elif method == 'UnloadUcp':
            self._doUnloadUcp(dialog)
            handled = True
        elif method == 'ViewUcp':
            self._doViewUcp(dialog)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        return ('external_event', 'Changed','LoadUcp', 'UnloadUcp', 'ViewUcp')

    def _loadSetting(self, dialog):
        msg = "OptionsDialog loading setting ... "
        control = dialog.getControl('ListBox1')
        control.Model.StringItemList = self._getProviders()
        self._doChanged(dialog, control)
        control = dialog.getControl('ListBox2')
        control.Model.StringItemList = self._getProviders(True)
        self._doChanged(dialog, control)
        msg += "Done"
        self.Logger.logp(INFO, 'OptionsDialog', '_loadSetting()', msg)

    def _saveSetting(self, dialog):
        pass

    def _doLoadUcp(self, dialog):
        control = dialog.getControl('ListBox1')
        scheme = control.SelectedItem
        identifier = getUcb(self.ctx).createContentIdentifier('%s:///' % scheme)
        control.Model.StringItemList = self._getProviders()
        self._doChanged(dialog, control)
        control = dialog.getControl('ListBox2')
        control.Model.StringItemList = self._getProviders(True)
        self._doChanged(dialog, control)

    def _doUnloadUcp(self, dialog):
        control = dialog.getControl('ListBox2')
        scheme = control.SelectedItem
        getUcp(self.ctx, scheme).deregisterInstance(scheme, '')
        control.Model.StringItemList = self._getProviders(True)
        self. _doChanged(dialog, control)
        control = dialog.getControl('ListBox1')
        control.Model.StringItemList = self._getProviders()
        self._doChanged(dialog, control)

    def _doChanged(self, dialog, control):
        enabled = control.SelectedItemPos != -1
        dialog.getControl(control.Model.Tag).Model.Enabled = enabled

    def _doViewUcp(self, dialog):
        service = "com.sun.star.ui.dialogs.FilePicker"
        fp = self.ctx.ServiceManager.createInstanceWithContext(service , self.ctx)
        fp.execute()
        fd.dispose()
        self._loadSetting(dialog)

    def _getProviders(self, loaded=False):
        schemes = []
        proxy = 'com.sun.star.ucb.ContentProviderProxy'
        infos = getUcb(self.ctx).queryContentProviders()
        for info in infos:
            provider = info.ContentProvider
            # provider can be None...
            if loaded:
                if not provider or provider.supportsService(proxy):
                    continue
            else:
                if provider and not provider.supportsService(proxy):
                    continue
            schemes.append(info.Scheme)
        return tuple(schemes)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(OptionsDialog,
                                         g_ImplementationName,
                                        (g_ImplementationName,))
