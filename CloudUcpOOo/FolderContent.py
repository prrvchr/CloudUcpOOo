#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContent
from com.sun.star.ucb import XCommandProcessor2
from com.sun.star.ucb import XContentCreator
from com.sun.star.ucb import InteractiveBadTransferURLException
from com.sun.star.ucb import CommandAbortedException
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.ContentAction import EXCHANGED
from com.sun.star.ucb.ContentAction import INSERTED

from clouducp import CommandInfo
from clouducp import CommandInfoChangeNotifier
from clouducp import DynamicResultSet
from clouducp import Initialization
from clouducp import PropertiesChangeNotifier
from clouducp import PropertyContainer
from clouducp import PropertySetInfo
from clouducp import PropertySetInfoChangeNotifier
from clouducp import Row
from clouducp import executeContentCommand
from clouducp import getCommandInfo
from clouducp import getContentEvent
from clouducp import getContentInfo
from clouducp import getLogger
from clouducp import getPropertiesValues
from clouducp import getProperty
from clouducp import getPropertyValueSet
from clouducp import getResourceLocation
from clouducp import getSimpleFile
from clouducp import getUcb
from clouducp import getUcp
from clouducp import isChildId
from clouducp import parseDateTime
from clouducp import propertyChange
from clouducp import selectChildId
from clouducp import setPropertiesValues
from clouducp import CREATED
from clouducp import FOLDER

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.CloudUcpOOo.FolderContent'


class FolderContent(unohelper.Base,
                    XServiceInfo,
                    XContent,
                    XChild,
                    XCommandProcessor2,
                    XContentCreator,
                    XCallback,
                    Initialization,
                    PropertyContainer,
                    PropertiesChangeNotifier,
                    PropertySetInfoChangeNotifier,
                    CommandInfoChangeNotifier):
    def __init__(self, ctx, *namedvalues):
        self.ctx = ctx
        self.Logger = getLogger(self.ctx)
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        msg = "DriveFolderContent loading ..."
        self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)
        self.Identifier = None
        self.ContentType = 'application/vnd.google-apps.folder'
        self.Name = 'Sans Nom'
        self.IsFolder = True
        self.IsDocument = False
        self.DateCreated = parseDateTime()
        self.DateModified = parseDateTime()
        self.MimeType = 'application/vnd.google-apps.folder'
        self.Size = 0
        self._Trashed = False

        self.CanAddChild = True
        self.CanRename = True
        self.IsReadOnly = False
        self.IsVersionable = False
        self._Loaded = 1

        self.IsHidden = False
        self.IsVolume = False
        self.IsRemote = False
        self.IsRemoveable = False
        self.IsFloppy = False
        self.IsCompactDisc = False

        self.listeners = []
        self.contentListeners = []
        self.propertiesListener = {}
        self.propertyInfoListeners = []
        self.commandInfoListeners = []
        self.commandIdentifier = 0

        self._newTitle = ''

        self.initialize(namedvalues)

        self._commandInfo = self._getCommandInfo()
        self._propertySetInfo = self._getPropertySetInfo()
        self._creatableContentsInfo = self._getCreatableContentsInfo()
        msg = "DriveFolderContent loading Uri: %s ... Done" % self.getIdentifier().getContentIdentifier()
        self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)

    @property
    def UserName(self):
        return self.getIdentifier().User.Name
    @property
    def Title(self):
        return self.Name
    @Title.setter
    def Title(self, title):
        identifier = self.getIdentifier()
        old = self.Name
        self.Name = title
        propertyChange(self, 'Name', old, title)
        event = getContentEvent(self, EXCHANGED, self, identifier)
        self.notify(event)
    @property
    def Trashed(self):
        return self._Trashed
    @Trashed.setter
    def Trashed(self, trashed):
        propertyChange(self, 'Trashed', self._Trashed, trashed)
    @property
    def MediaType(self):
        return self.MimeType
    @property
    def Loaded(self):
        return self._Loaded
    @Loaded.setter
    def Loaded(self, loaded):
        propertyChange(self, 'Loaded', self._Loaded, loaded)
        self._Loaded = loaded
    @property
    def CreatableContentsInfo(self):
        return self._creatableContentsInfo

    # XCallback
    def notify(self, event):
        for listener in self.contentListeners:
            listener.contentEvent(event)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        return self._creatableContentsInfo
    def createNewContent(self, contentinfo):
        identifier = self.getIdentifier().createContentIdentifier(self._newTitle)
        self._newTitle = ''
        return identifier.getInstance(contentinfo.Type)

    # XChild
    def getParent(self):
        identifier = self.getIdentifier()
        if identifier.IsRoot:
            raise NoSupportException('Root Folder as no Parent', self)
        return getUcb(self.ctx).queryContent(identifier.getParent())
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        return self.Identifier
    def getContentType(self):
        return self.ContentType
    def addContentEventListener(self, listener):
        if listener not in self.contentListeners:
            self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        if command.Name == 'getCommandInfo':
            return CommandInfo(self._commandInfo)
        elif command.Name == 'getPropertySetInfo':
            return PropertySetInfo(self._propertySetInfo)
        elif command.Name == 'getPropertyValues':
            namedvalues = getPropertiesValues(self, command.Argument, self.Logger)
            return Row(namedvalues)
        elif command.Name == 'setPropertyValues':
            return setPropertiesValues(self, environment, command.Argument, self._propertySetInfo, self.Logger)
        elif command.Name == 'open':
            print("DriveFolderContent.execute() open 1")
            identifier = self.getIdentifier()
            if self.Loaded == ONLINE:
                identifier.updateLinks()
                if identifier.Updated:
                    self.Loaded = OFFLINE
            # Not Used: command.Argument.Properties - Implement me ;-)
            print("DriveFolderContent.execute() open 2")
            return DynamicResultSet(self.ctx, identifier)
        elif command.Name == 'insert':
            print("DriveFolderContent.execute() insert")
            identifier = self.getIdentifier()
            ucp = getUcp(self.ctx, identifier.getContentProviderScheme())
            self.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), ucp)
            propertyChange(self, 'Id', identifier.Id, CREATED | FOLDER)
            parent = identifier.getParent()
            event = getContentEvent(self, INSERTED, self, parent)
            ucp.queryContent(parent).notify(event)
        elif command.Name == 'delete':
            print("DriveFolderContent.execute(): delete")
            self.Trashed = True
        elif command.Name == 'createNewContent':
            print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
            return self.createNewContent(command.Argument)
        elif command.Name == 'transfer':
            # Transfer command is used for document 'File Save' or 'File Save As'
            # NewTitle come from:
            # - Last segment path of 'XContent.getIdentifier().getContentIdentifier()' for OpenOffice
            # - Property 'Title' of 'XContent' for LibreOffice
            # If the content has been renamed, the last segment is the new Title of the content
            title = command.Argument.NewTitle
            source = command.Argument.SourceURL
            move = command.Argument.MoveData
            clash = command.Argument.NameClash
            print("DriveFolderContent.execute(): transfer 1:\nSource:    %s\nId:    %s\nMove:    %s\nClash:    %s" % (source, title, move, clash))
            identifier = self.getIdentifier()
            # We check if 'command.Argument.NewTitle' is an Id
            if isChildId(identifier, title):
                id = title
            else:
                # It appears that 'command.Argument.NewTitle' is not an Id but a Title...
                # If 'NewTitle' exist and is unique in the folder, we can retrieve its Id
                id = selectChildId(identifier.User.Connection, identifier.Id, title)
                if id is None:
                    # Id could not be found: NewTitle does not exist in the folder...
                    # For new document (File Save As) we use commands:
                    # - createNewContent: for creating an empty new Content
                    # - Insert at new Content for committing change
                    # To execute these commands, we must throw an exception
                    # But we need to keep 'NewTitle' for building the Uri
                    self._newTitle = title
                    print("DriveFolderContent.execute(): transfer 2:\n    transfer: %s - %s" % (source, id))
                    raise InteractiveBadTransferURLException("Couln't handle Url: %s" % source, self)
            print("DriveFolderContent.execute(): transfer 3:\n    transfer: %s - %s" % (source, id))
            sf = getSimpleFile(self.ctx)
            if not sf.exists(source):
                raise CommandAbortedException("Error while saving file: %s" % source, self)
            inputstream = sf.openFileRead(source)
            target = '%s/%s' % (identifier.SourceURL, id)
            sf.writeFile(target, inputstream)
            inputstream.closeInput()
            ucb = getUcb(self.ctx)
            identifier = ucb.createContentIdentifier('%s/%s' % (identifier.BaseURL, title))
            data = getPropertyValueSet({'Size': sf.getSize(target)})
            content = ucb.queryContent(identifier)
            executeContentCommand(content, 'setPropertyValues', data, environment)
            print("DriveFolderContent.execute(): transfer 4: Fin")
            if command.Argument.MoveData:
                pass #must delete object
        elif command.Name == 'flush':
            print("DriveFolderContent.execute(): flush")
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = getCommandInfo('getCommandInfo')
        commands['getPropertySetInfo'] = getCommandInfo('getPropertySetInfo')
        commands['getPropertyValues'] = getCommandInfo('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = getCommandInfo('setPropertyValues', '[]com.sun.star.beans.PropertyValue')
        commands['open'] = getCommandInfo('open', 'com.sun.star.ucb.OpenCommandArgument2')
        commands['createNewContent'] = getCommandInfo('createNewContent', 'com.sun.star.ucb.ContentInfo')
        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument')
        if not self.getIdentifier().IsRoot:
            commands['delete'] = getCommandInfo('delete', 'boolean')
        commands['transfer'] = getCommandInfo('transfer', 'com.sun.star.ucb.TransferInfo')
        commands['flush'] = getCommandInfo('flush')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        constrained = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.CONSTRAINED')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MimeType'] = getProperty('MimeType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound | constrained)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['Loaded'] = getProperty('Loaded', 'long', bound)
        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', bound | readonly)

        properties['IsHidden'] = getProperty('IsHidden', 'boolean', bound | readonly)
        properties['IsVolume'] = getProperty('IsVolume', 'boolean', bound | readonly)
        properties['IsRemote'] = getProperty('IsRemote', 'boolean', bound | readonly)
        properties['IsRemoveable'] = getProperty('IsRemoveable', 'boolean', bound | readonly)
        properties['IsFloppy'] = getProperty('IsFloppy', 'boolean', bound | readonly)
        properties['IsCompactDisc'] = getProperty('IsCompactDisc', 'boolean', bound | readonly)
        return properties

    def _getCreatableContentsInfo(self):
        if not self.CanAddChild:
            return ()
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        foldertype = 'application/vnd.google-apps.folder'
        officetype = 'application/vnd.oasis.opendocument'
        documenttype = 'application/vnd.google-apps.document'
        properties = (getProperty('Title', 'string', bound), )
        content = (getContentInfo(foldertype, folder, properties),
                   getContentInfo(officetype, document, properties),
                   getContentInfo(documenttype, document, properties))
        return content

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(FolderContent,                                                      # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.Content'))                  # List of implemented services
