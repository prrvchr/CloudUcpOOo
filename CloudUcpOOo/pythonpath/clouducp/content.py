#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.uno import XInterface
from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContent
from com.sun.star.ucb import XCommandProcessor2
from com.sun.star.ucb import XContentCreator
from com.sun.star.ucb import InteractiveBadTransferURLException
from com.sun.star.ucb import CommandAbortedException
from com.sun.star.beans.PropertyAttribute import BOUND
from com.sun.star.beans.PropertyAttribute import CONSTRAINED
from com.sun.star.beans.PropertyAttribute import READONLY
from com.sun.star.beans.PropertyAttribute import TRANSIENT
from com.sun.star.ucb.ContentInfoAttribute import KIND_DOCUMENT
from com.sun.star.ucb.ContentInfoAttribute import KIND_FOLDER
from com.sun.star.ucb.ContentInfoAttribute import KIND_LINK
from com.sun.star.ucb.ContentAction import INSERTED
from com.sun.star.ucb.ContentAction import EXCHANGED
from com.sun.star.logging.LogLevel import INFO

# oauth2 is only available after OAuth2OOo as been loaded...
try:
    from oauth2 import KeyMap
except ImportError:
    pass

from .contentlib import CommandInfo
from .contentlib import Row
from .contentlib import DynamicResultSet
from .unolib import PropertySetInfo

from .contentcore import getPropertiesValues
from .contentcore import setPropertiesValues
from .contenttools import getCommandInfo
from .contenttools import getContentInfo
from .contenttools import getUcb
from .contenttools import getUcp
from .contenttools import getUri
from .contenttools import getMimeType
from .unotools import getSimpleFile
from .unotools import getProperty
from .unotools import getPropertyValueSet
from .logger import getLogger

import traceback


class Content(unohelper.Base,
              XContent,
              XCommandProcessor2,
              XContentCreator,
              XChild):
    def __init__(self, ctx, identifier, data):
        try:
            self.ctx = ctx
            msg = "DriveFolderContent loading ... "
            self.Identifier = identifier
            self.MetaData = data
            creatablecontent = self._getCreatableContentsInfo()
            self.MetaData.insertValue('CreatableContentsInfo', creatablecontent)
            self._commandInfo = self._getCommandInfo()
            self._propertySetInfo = self._getPropertySetInfo()
            self.contentListeners = []
            msg += "Done."
            if self.Logger:
                self.Logger.logp(INFO, "DriveFolderContent", "__init__()", msg)
            print("Content.__init__() FIN")
        except Exception as e:
            print("Content.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    @property
    def IsFolder(self):
        return self.MetaData.getValue('IsFolder')
    @property
    def IsDocument(self):
        return self.MetaData.getValue('IsDocument')
    @property
    def CanAddChild(self):
        return self.MetaData.getValue('CanAddChild')
    @property
    def Logger(self):
        return self.Identifier.User.DataSource.Provider.Request.Logger

    # XChild
    def getParent(self):
        if self.Identifier.IsRoot:
            print("Content.getParent() 1")
            return XInterface()
        identifier = self.Identifier.getParent()
        print("Content.getParent() 2 %s" % identifier.getContentIdentifier())
        return identifier.getContent()
    def setParent(self, parent):
        print("Content.setParent()")
        raise NoSupportException('Parent can not be set', self)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        return self.MetaData.getValue('CreatableContentsInfo')
    def createNewContent(self, info):
        try:
            print("Content.createNewContent() 1 %s" % info)
            identifier = self.Identifier.createNewIdentifier(info.Type)
            print("Content.createNewContent() 2 %s" % info.Type)
            return identifier.getContent()
        except Exception as e:
            print("Content.createNewContent().Error: %s - %s" % (e, traceback.print_exc()))

    # XContent
    def getIdentifier(self):
        print("Content.getIdentifier()")
        return self.Identifier
    def getContentType(self):
        print("Content.getContentType()")
        return self.MetaData.getValue('ContentType')
    def addContentEventListener(self, listener):
        print("Content.addContentEventListener()")
        if listener not in self.contentListeners:
            self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("Content.removeContentEventListener()")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        try:
            print("Content.execute(): %s" % command.Name)
            if command.Name == 'getCommandInfo':
                return CommandInfo(self._commandInfo)
            elif command.Name == 'getPropertySetInfo':
                return PropertySetInfo(self._propertySetInfo)
            elif command.Name == 'getPropertyValues':
                namedvalues = getPropertiesValues(self, command.Argument, self.Logger)
                return Row(namedvalues)
            elif command.Name == 'setPropertyValues':
                return setPropertiesValues(self, environment, command.Argument, self.Logger)
            elif command.Name == 'delete':
                print("Content.execute(): delete")
                self.MetaData.insertValue('Trashed', self.Identifier.updateTrashed(True, False))
            elif command.Name == 'open':
                if self.IsFolder:
                    # Not Used: command.Argument.Properties - Implement me ;-)
                    select = self.Identifier.getFolderContent(self.MetaData)
                    return DynamicResultSet(self.ctx, select)
                elif self.IsDocument:
                    sf = getSimpleFile(self.ctx)
                    url, size = self.Identifier.getDocumentContent(sf, self.MetaData, 0)
                    if not size:
                        title = self.MetaData.getValue('Title')
                        msg = "Error while downloading file: %s" % title
                        raise CommandAbortedException(msg, self)
                    s = command.Argument.Sink
                    sink = uno.getTypeByName('com.sun.star.io.XActiveDataSink')
                    stream = uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')
                    isreadonly = self.MetaData.getValue('IsReadOnly')
                    if s.queryInterface(sink):
                        s.setInputStream(sf.openFileRead(url))
                    elif not isreadonly and s.queryInterface(stream):
                        s.setStream(sf.openFileReadWrite(url))
            elif command.Name == 'insert':
                if self.IsFolder:
                    print("Content.execute() insert")
                    mediatype = self.Identifier.User.DataSource.Provider.Folder
                    self.MetaData.insertValue('MediaType', mediatype)
                    if self.Identifier.insertNewFolder(self.MetaData):
                        print("Content.execute(): insert %s" % mediatype)
                    #identifier = self.getIdentifier()
                    #ucp = getUcp(self.ctx, identifier.getContentProviderScheme())
                    #self.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), ucp)
                    #propertyChange(self, 'Id', identifier.Id, CREATED | FOLDER)
                    #parent = identifier.getParent()
                    #event = getContentEvent(self, INSERTED, self, parent)
                    #ucp.queryContent(parent).notify(event)
                elif self.IsDocument:
                    # The Insert command is only used to create a new document (File Save As)
                    # it saves content from createNewContent from the parent folder
                    print("Content.execute(): insert %s" % command.Argument)
                    stream = command.Argument.Data
                    replace = command.Argument.ReplaceExisting
                    sf = getSimpleFile(self.ctx)
                    url = self.Identifier.User.DataSource.Provider.SourceURL
                    target = '%s/%s' % (url, self.Identifier.Id)
                    if sf.exists(target) and not replace:
                        pass
                    elif stream.queryInterface(uno.getTypeByName('com.sun.star.io.XInputStream')):
                        sf.writeFile(target, stream)
                        mediatype = getMimeType(self.ctx, stream)
                        self.MetaData.insertValue('MediaType', mediatype)
                        stream.closeInput()
                        if self.Identifier.insertNewDocument(self.MetaData):
                            print("Content.execute(): insert %s" % mediatype)
                        #ucp = getUcp(self.ctx, identifier.getContentProviderScheme())
                        #self.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), ucp)
                        #propertyChange(self, 'Id', identifier.Id, CREATED | FILE)
                        #parent = identifier.getParent()
                        #event = getContentEvent(self, INSERTED, self, parent)
                        #ucp.queryContent(parent).notify(event)
                print("Content.execute(): insert FIN")
            elif command.Name == 'createNewContent' and self.IsFolder:
                print("Content.execute(): createNewContent %s" % command.Argument)
                return self.createNewContent(command.Argument)
            elif command.Name == 'transfer' and self.IsFolder:
                # Transfer command is used for document 'File Save' or 'File Save As'
                # NewTitle come from:
                # - Last segment path of 'XContent.getIdentifier().getContentIdentifier()' for OpenOffice
                # - Property 'Title' of 'XContent' for LibreOffice
                # If the content has been renamed, the last segment is the new Title of the content
                title = command.Argument.NewTitle
                source = command.Argument.SourceURL
                move = command.Argument.MoveData
                clash = command.Argument.NameClash
                print("Content.execute(): transfer 1:\nSource: %s\nId: %s\nMove: %s\nClash: %s" \
                                 % (source, title, move, clash))
                # We check if 'command.Argument.NewTitle' is an Id
                if self.Identifier.isChildId(title):
                    id = title
                else:
                    # It appears that 'command.Argument.NewTitle' is not an Id but a Title...
                    # If 'NewTitle' exist and is unique in the folder, we can retrieve its Id
                    id = self.Identifier.selectChildId(title)
                    if not id:
                        # Id could not be found: NewTitle does not exist in the folder...
                        # For new document (File Save As) we use commands:
                        # - createNewContent: for creating an empty new Content
                        # - Insert at new Content for committing change
                        # To execute these commands, we must throw an exception
                        msg = "Couln't handle Url: %s" % source
                        print("Content.execute(): transfer 2:\n    transfer: %s - %s" % (source, id))
                        raise InteractiveBadTransferURLException(msg, self)
                print("Content.execute(): transfer 3:\n    transfer: %s - %s" % (source, id))
                sf = getSimpleFile(self.ctx)
                if not sf.exists(source):
                    raise CommandAbortedException("Error while saving file: %s" % source, self)
                inputstream = sf.openFileRead(source)
                target = '%s/%s' % (self.Identifier.User.DataSource.Provider.SourceURL, id)
                sf.writeFile(target, inputstream)
                inputstream.closeInput()
                # We need to commit change: Size is the property chainning all DataSource change
                if not self.Identifier.User.updateSize(id, self.Identifier.Id, sf.getSize(target)):
                    print("Content.execute(): transfer 4: ERROR")
                    raise CommandAbortedException("Error while saving file: %s" % source, self)
                #ucb = getUcb(self.ctx)
                #identifier = ucb.createContentIdentifier('%s/%s' % (self.Identifier.BaseURL, title))
                #data = getPropertyValueSet({'Size': sf.getSize(target)})
                #content = ucb.queryContent(identifier)
                #executeContentCommand(content, 'setPropertyValues', data, environment)
                print("Content.execute(): transfer 4: FIN")
                if move:
                    pass #must delete object
            elif command.Name == 'flush' and self.IsFolder:
                print("Content.execute(): flush")
        except InteractiveBadTransferURLException as e:
            raise e
        except Exception as e:
            print("Content.execute().Error: %s - %s - %s" % (command.Name, e, traceback.print_exc()))

    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _getCreatableContentsInfo(self):
        content = []
        if self.IsFolder and self.CanAddChild:
            provider = self.Identifier.User.DataSource.Provider
            properties = (getProperty('Title', 'string', BOUND), )
            content.append(getContentInfo(provider.Folder, KIND_FOLDER, properties))
            content.append(getContentInfo(provider.Office, KIND_DOCUMENT, properties))
            #if provider.hasProprietaryFormat:
            #    content.append(getContentInfo(provider.ProprietaryFormat, KIND_DOCUMENT, properties))
        return tuple(content)

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = getCommandInfo('getCommandInfo')
        commands['getPropertySetInfo'] = getCommandInfo('getPropertySetInfo')
        commands['getPropertyValues'] = getCommandInfo('getPropertyValues',
                                                        '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = getCommandInfo('setPropertyValues',
                                                        '[]com.sun.star.beans.PropertyValue')
        commands['open'] = getCommandInfo('open', 'com.sun.star.ucb.OpenCommandArgument2')
        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument')
        if not self.Identifier.IsRoot:
            commands['delete'] = getCommandInfo('delete', 'boolean')
        if self.CanAddChild:
            commands['createNewContent'] = getCommandInfo('createNewContent', 'com.sun.star.ucb.ContentInfo')
            commands['transfer'] = getCommandInfo('transfer', 'com.sun.star.ucb.TransferInfo')
            commands['flush'] = getCommandInfo('flush')
        return commands

    def _getPropertySetInfo(self):
        RO = 0 if self.Identifier.IsNew else READONLY
        properties = {}
        properties['ContentType'] = getProperty('ContentType', 'string', BOUND | RO)
        properties['MediaType'] = getProperty('MediaType', 'string', BOUND | READONLY)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', BOUND | RO)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', BOUND | RO)
        properties['Title'] = getProperty('Title', 'string', BOUND | CONSTRAINED)
        properties['Size'] = getProperty('Size', 'long', BOUND | RO)
        created = getProperty('DateCreated', 'com.sun.star.util.DateTime', BOUND | READONLY)
        properties['DateCreated'] = created
        modified = getProperty('DateModified', 'com.sun.star.util.DateTime', BOUND | RO)
        properties['DateModified'] = modified
        properties['IsReadOnly'] = getProperty('IsReadOnly', 'boolean', BOUND | RO)
        info = getProperty('CreatableContentsInfo','[]com.sun.star.ucb.ContentInfo', BOUND | RO)
        properties['CreatableContentsInfo'] = info
        properties['CasePreservingURL'] = getProperty('CasePreservingURL', 'string', BOUND | RO)
        properties['BaseURI'] = getProperty('BaseURI', 'string', BOUND | READONLY)
        properties['TitleOnServer'] = getProperty('TitleOnServer', 'string', BOUND)
        properties['IsHidden'] = getProperty('IsHidden', 'boolean', BOUND | RO)
        properties['IsVolume'] = getProperty('IsVolume', 'boolean', BOUND | RO)
        properties['IsRemote'] = getProperty('IsRemote', 'boolean', BOUND | RO)
        properties['IsRemoveable'] = getProperty('IsRemoveable', 'boolean', BOUND | RO)
        properties['IsFloppy'] = getProperty('IsFloppy', 'boolean', BOUND | RO)
        properties['IsCompactDisc'] = getProperty('IsCompactDisc', 'boolean', BOUND | RO)
        return properties
