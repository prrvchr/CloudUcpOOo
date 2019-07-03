#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.awt import XDialogEventHandler

import traceback

try:
    from clouducp import g_identifier
    from clouducp import createService
    from clouducp import getFileSequence
    from clouducp import getLogger
    from clouducp import getLoggerUrl
    from clouducp import getLoggerSetting
    from clouducp import getStringResource
    from clouducp import getUcb
    from clouducp import getUcp
    from clouducp import setLoggerSetting
    from clouducp import getConfiguration
    from clouducp import getNamedValueSet
except ImportError as e:
    print("OptionsDialog.import().Error: %s - %s" % (e, traceback.print_exc()))


# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.OptionsDialog' % g_identifier


class OptionsDialog(unohelper.Base,
                    XServiceInfo,
                    XContainerWindowEventHandler,
                    XDialogEventHandler):
    def __init__(self, ctx):
        self.ctx = ctx
        self.stringResource = getStringResource(self.ctx, g_identifier, 'CloudUcpOOo')
        print("OptionsDialog.__init__() 1")

    def __del__(self):
        print("OptionsDialog.__del__()***********************")

    # XContainerWindowEventHandler, XDialogEventHandler
    def callHandlerMethod(self, dialog, event, method):
        print("OptionsDialog.callHandlerMethod() 1")
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
        elif method == 'Logger':
            self._doLogger(dialog, bool(event.Source.State))
            handled = True
        elif method == 'ViewLog':
            self._doViewLog(dialog)
            handled = True
        elif method == 'ClearLog':
            self._doClearLog(dialog)
            handled = True
        elif method == 'LoadUcp':
            self._doLoadUcp(dialog)
            handled = True
        elif method == 'UnloadUcp':
            self._doUnloadUcp(dialog)
            handled = True
        elif method == 'Changed':
            self._doChanged(dialog, event.Source)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        print("OptionsDialog.getSupportedMethodNames() 1")
        return ('external_event', 'Logger', 'ViewLog', 'ClearLog', 'Changed', 'LoadUcp', 'UnloadUcp')

    def _doChanged(self, dialog, control):
        enabled = control.SelectedItemPos != -1
        dialog.getControl(control.Model.Tag).Model.Enabled = enabled
        print("OptionsDialog._doChanged() 1")

    def _loadSetting(self, dialog):
        try:
            print("OptionsDialog._loadSetting() 1")
            self._loadLoggerSetting(dialog)
            self._loadUcpSetting(dialog)
        except Exception as e:
            print("OptionsDialog._loadSetting().Error: %s - %s" % (e, traceback.print_exc()))

    def _saveSetting(self, dialog):
        self._saveLoggerSetting(dialog)

    def _toogleSync(self, dialog, enabled):
        dialog.getControl('CommandButton2').Model.Enabled = not enabled

    def _doLogger(self, dialog, enabled):
        dialog.getControl('Label2').Model.Enabled = enabled
        dialog.getControl('ComboBox1').Model.Enabled = enabled
        dialog.getControl('OptionButton1').Model.Enabled = enabled
        dialog.getControl('OptionButton2').Model.Enabled = enabled
        dialog.getControl('CommandButton1').Model.Enabled = enabled

    def _doViewLog(self, window):
        try:
            url = getLoggerUrl(self.ctx)
            length, sequence = getFileSequence(self.ctx, url)
            text = sequence.value.decode('utf-8')
            dialog = self._getLogDialog(window)
            dialog.Title = url
            dialog.getControl('TextField1').Text = text
            dialog.execute()
            dialog.dispose()
        except Exception as e:
            print("OptionsDialog._doViewLog().Error: %s - %s" % (e, traceback.print_exc()))

    def _doClearLog(self, dialog):
        try:
            url = getLoggerUrl(self.ctx)
            sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
            if sf.exists(url):
                sf.kill(url)
            service = 'org.openoffice.logging.FileHandler'
            args = getNamedValueSet({'FileURL': url})
            handler = self.ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, args, self.ctx)
            logger = getLogger(self.ctx)
            logger.addLogHandler(handler)
            length, sequence = getFileSequence(self.ctx, url)
            text = sequence.value.decode('utf-8')
            dialog.getControl('TextField1').Text = text
            print("OptionsDialog._doClearLog() 1")
        except Exception as e:
            print("OptionsDialog._doClearLog().Error: %s - %s" % (e, traceback.print_exc()))

    def _doLoadUcp(self, dialog):
        try:
            print("OptionsDialog._doLoadUcp() 1")
            scheme = dialog.getControl('ListBox1').SelectedItem
            provider = self._getProvider(scheme)
            if provider.supportsService('com.sun.star.ucb.ContentProviderProxy'):
                print("OptionsDialog._doLoadUcp() 2")
                provider = provider.getContentProvider()
                control = dialog.getControl('ListBox2')
                control.Model.StringItemList = self._getSchemes(True)
                self. _doChanged(dialog, control)
            print("OptionsDialog._doLoadUcp() 3")
        except Exception as e:
            print("OptionsDialog._doLoadUcp().Error: %s - %s" % (e, traceback.print_exc()))

    def _doUnloadUcp(self, dialog):
        try:
            control = dialog.getControl('ListBox2')
            scheme = control.SelectedItem
            self._getProvider(scheme).deregisterInstance(scheme, '')
            control.Model.StringItemList = self._getSchemes(True)
            self. _doChanged(dialog, control)
            print("OptionsDialog._doUnloadUcp() 1")
        except Exception as e:
            print("OptionsDialog._doUnloadUcp().Error: %s - %s" % (e, traceback.print_exc()))

    def _getLogDialog(self, window):
        url = 'vnd.sun.star.script:CloudUcpOOo.LogDialog?location=application'
        service = 'com.sun.star.awt.DialogProvider'
        provider = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        #mri.inspect(window)
        arguments = getNamedValueSet({'ParentWindow': window.Peer, 'EventHandler': self})
        dialog = provider.createDialogWithArguments(url, arguments)
        return dialog

    def _loadLoggerSetting(self, dialog):
        try:
            enabled, index, handler = getLoggerSetting(self.ctx)
            print("OptionsDialog._loadLoggerSetting() %s %s %s" % (enabled, index, handler))
            dialog.getControl('CheckBox1').State = int(enabled)
            print("OptionsDialog._loadLoggerSetting() 2")
            self._setLoggerLevel(dialog.getControl('ComboBox1'), index)
            print("OptionsDialog._loadLoggerSetting() 3")
            dialog.getControl('OptionButton%s' % handler).State = 1
            print("OptionsDialog._loadLoggerSetting() 4")
            self._doLogger(dialog, enabled)
            print("OptionsDialog._loadLoggerSetting() 5")
        except Exception as e:
            print("OptionsDialog._loadLoggerSetting().Error: %s - %s" % (e, traceback.print_exc()))

    def _loadUcpSetting(self, dialog):
        dialog.getControl('ListBox1').Model.StringItemList = self._getSchemes()
        dialog.getControl('ListBox2').Model.StringItemList = self._getSchemes(True)

    def _getSchemes(self, loaded=False):
        schemes = []
        for info in getUcb(self.ctx).queryContentProviders():
            provider = info.ContentProvider
            if loaded:
                if not provider or provider.supportsService('com.sun.star.ucb.ContentProviderProxy'):
                    continue
            schemes.append(info.Scheme)
        return tuple(schemes)

    def _getProvider(self, scheme):
        provider = None
        for info in getUcb(self.ctx).queryContentProviders():
            if info.Scheme == scheme:
                provider = info.ContentProvider
                break
        return provider

    def _setLoggerLevel(self, control, index):
        name = control.Model.Name
        text = self.stringResource.resolveString('OptionsDialog.%s.StringItemList.%s' % (name, index))
        control.Text = text

    def _getLoggerLevel(self, control):
        name = control.Model.Name
        for index in range(control.ItemCount):
            text = self.stringResource.resolveString('OptionsDialog.%s.StringItemList.%s' % (name, index))
            if text == control.Text:
                break
        return index

    def _saveLoggerSetting(self, dialog):
        enabled = bool(dialog.getControl('CheckBox1').State)
        index = self._getLoggerLevel(dialog.getControl('ComboBox1'))
        handler = dialog.getControl('OptionButton1').State
        setLoggerSetting(self.ctx, enabled, index, handler)

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
