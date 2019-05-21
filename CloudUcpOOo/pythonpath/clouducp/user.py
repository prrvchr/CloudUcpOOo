#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import XRestUser

from .keymap import KeyMap

import traceback


class User(unohelper.Base,
           XRestUser):
    def __init__(self, ctx, datasource, name):
        self.ctx = ctx
        self.Name = name
        self.DataSource = datasource
        self._Error = ''
        self.MetaData, self._Error = self.DataSource.initializeUser(name, '')
        if self.IsValid:
            self.checkNewIdentifier()

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('UserId', None)
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
    def Error(self):
        return self.DataSource.Error if self.DataSource.Error else self._Error

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
    def getFolderContent(self, identifier, content, index, updated):
        return self.DataSource.getFolderContent(self.MetaData, identifier, content, index, updated)

    def updateLoaded(self, itemid, value, default):
        return self.DataSource.updateLoaded(self.Id, itemid, value, default)
    def updateTitle(self, itemid, value, default):
        return self.synchronize(self.DataSource.updateTitle(self.Id, itemid, value, default))
    def updateSize(self, itemid, size):
        return self.synchronize(self.DataSource.updateSize(self.Id, itemid, size))
    def updateTrashed(self, itemid, value, default):
        return self.synchronize(self.DataSource.updateTrashed(self.Id, itemid, value, default))

    def checkNewIdentifier(self):
        self.DataSource.checkNewIdentifier(self.MetaData)
    def getNewIdentifier(self):
        return self.DataSource.getNewIdentifier(self.MetaData)

    def getInputStream(self, url):
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def initializeIdentifier(self, uri, isnew, error=''):
        paths = []
        position = -1
        basename = ''
        parent = self.RootId
        isroot = False
        for i in range(uri.getPathSegmentCount() -1, -1, -1):
            path = uri.getPathSegment(i).strip()
            if path not in ('','.'):
                if not basename:
                    basename = path
                    position = i
                else:
                    parent = path
                    break
        for i in range(position):
            paths.append(uri.getPathSegment(i).strip())
        if not basename:
            id = self.RootId
            isroot = True
        elif isnew:
            id = self.getNewIdentifier()
        elif self.isIdentifier(basename):
            id = basename
        else:
            id = self.selectChildId(parent, basename)
        if not id:
            id = self._searchId(paths[::-1], basename)
        if not id:
            error = "ERROR: Can't retrieve Uri: %s" % uri.getUriReference()
            print("User.initializeIdentifier() Error: %s" % error)
        paths.insert(0, self.Name)
        identifier = KeyMap(**{'Id': id})
        identifier.insertValue('IsRoot', isroot)
        identifier.insertValue('IsNew', isnew)
        identifier.insertValue('BaseName', basename)
        identifier.insertValue('BaseURI', '%s://%s' % (uri.getScheme(), '/'.join(paths)))
        print("User.initializeIdentifier() FIN")
        return identifier, error

    def synchronize(self, value):
        return self.DataSource.synchronize(self.MetaData, value)

    def _searchId(self, paths, basename):
        # Needed for be able to create a folder in a just created folder...
        id = ''
        paths.append(self.RootId)
        for i, path in enumerate(paths):
            if self.isIdentifier(path):
                id = path
                break
        for j in range(i -1, -1, -1):
            id = self.selectChildId(id, paths[j])
        id = self.selectChildId(id, basename)
        return id
