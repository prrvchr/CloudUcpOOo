#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import XRestUser

from .identifier import Identifier
from .keymap import KeyMap

import traceback


class User(unohelper.Base,
           XRestUser):
    def __init__(self, ctx, datasource):
        level = INFO
        msg = "User loading"
        self.ctx = ctx
        self.DataSource = datasource
        self.MetaData = KeyMap()
        self._Error = ''
        msg += " ... Done"
        self.Logger.logp(level, "User", "__init__()", msg)

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('UserId', None)
    @property
    def Name(self):
        return self.MetaData.getDefaultValue('Name', None)
    @property
    def RootId(self):
        return self.MetaData.getDefaultValue('RootId', None)
    @property
    def RootName(self):
        return self.MetaData.getDefaultValue('RootName', None)
    @property
    def IsValid(self):
        return all((self.Id, self.Name, self.RootId, self.RootName, not self.Error))
    @property
    def Logger(self):
        return self.DataSource.Logger
    @property
    def Error(self):
        return self.DataSource.Error if self.DataSource.Error else self._Error

    def initialize(self, name):
        print("User.initialize() 1")
        if name == '':
            self._Error = "ERROR: Can't retrieve a UserName from Handler"
            return False
        elif not self.DataSource.initializeUser(name):
            return False
        self.MetaData = self.DataSource.getUser(name)
        print("User.initialize() 2")
        return True

    def isChildId(self, itemid, title):
        return self.DataSource.isChildId(self.Id, itemid, title)
    def selectChildId(self, parent, title):
        return self.DataSource.selectChildId(self.Id, parent, title)
    def countChildTitle(self, parent, title):
        return self.DataSource.countChildTitle(self.Id, parent, title)

    def isIdentifier(self, id):
        return self.DataSource.isIdentifier(self.Id, id)

    def getItem(self, identifier):
        return self.DataSource.getItem(self.MetaData, identifier)

    def insertNewDocument(self, itemid, parentid, content):
        inserted = self.DataSource.insertNewDocument(self.Id, itemid, parentid, content)
        return self.synchronize(inserted)
    def insertNewFolder(self, itemid, parentid, content):
        inserted = self.DataSource.insertNewFolder(self.Id, itemid, parentid, content)
        return self.synchronize(inserted)

    # XRestUser
    def getFolderContent(self, identifier, content, updated):
        return self.DataSource.getFolderContent(self.MetaData, identifier, content, updated)

    def updateLoaded(self, itemid, value, default):
        return self.DataSource.updateLoaded(self.Id, itemid, value, default)
    def updateTitle(self, itemid, parentid, value, default):
        return self.synchronize(self.DataSource.updateTitle(self.Id, itemid, parentid, value, default))
    def updateSize(self, itemid, parentid, size):
        return self.synchronize(self.DataSource.updateSize(self.Id, itemid, parentid, size))
    def updateTrashed(self, itemid, parentid, value, default):
        return self.synchronize(self.DataSource.updateTrashed(self.Id, itemid, parentid, value, default))

    def checkNewIdentifier(self):
        self.DataSource.checkNewIdentifier(self.MetaData)
    def getNewIdentifier(self):
        return self.DataSource.getNewIdentifier(self.MetaData)

    def getInputStream(self, url):
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def getIdentifier(self, url):
        print("User.getIdentifier() *****************************************************")
        return Identifier(self.ctx, self, url)

    def synchronize(self, value):
        return self.DataSource.synchronize(self.MetaData, value)
