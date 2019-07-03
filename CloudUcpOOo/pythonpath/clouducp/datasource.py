#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.util import XCloseListener
from com.sun.star.lang import XEventListener
from com.sun.star.sdb.CommandType import QUERY
from com.sun.star.ucb import XRestDataSource
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RETRIEVED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_CREATED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FOLDER
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FILE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RENAMED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_REWRITED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_TRASHED

from .user import User

from .datasourcehelper import getDataSourceUrl
from .datasourcehelper import getDataSourceConnection
from .datasourcehelper import getKeyMapFromResult
from .datasourcequeries import getSqlQuery
from .dbtools import parseDateTime
from .unotools import getResourceLocation
from .unotools import getPropertyValue

import binascii
import traceback


class DataSource(unohelper.Base,
                 XCloseListener,
                 XRestDataSource):
    def __init__(self, ctx, scheme, plugin):
        try:
            self.ctx = ctx
            print("DataSource.__init__() 1")
            service = '%s.Provider' % plugin
            self.Provider = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
            print("DataSource.__init__() 2")
            self._Statement = None
            self._CahedUser = {}
            self._Calls = {}
            self._Error = ''
            url = getDataSourceUrl(ctx, scheme, plugin)
            print("DataSource.__init__() 3")
            connection = getDataSourceConnection(ctx, url)
            if not connection:
                self._Error = "Could not connect to DataSource at URL: %s" % url
            else:
                # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
                self._Statement = connection.createStatement()
                folder, link = self._getContentType()
                print("DataSource.__init__() 4 %s - %s" % (link, folder))
                self.Provider.initialize(scheme, plugin, folder, link)
            print("DataSource.__init__() FIN")
        except Exception as e:
            print("DataSource.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    @property
    def Connection(self):
        return self._Statement.getConnection()
    @property
    def IsValid(self):
        return not self.Error
    @property
    def Error(self):
        return self.Provider.Error if self.Provider else self._Error

    def getUser(self, name):
        # User never change... we can cache it...
        if name and name in self._CahedUser:
            user = self._CahedUser[name]
        else:
            user = User(self.ctx, self, name)
            if user.IsValid:
                self._CahedUser[name] = user
        return user

    def initializeUser(self, name, error):
        try:
            print("DataSource.initializeUser() 1")
            user = self.Provider.Request.getKeyMap()
            if not name:
                error = "ERROR: Can't retrieve a UserName from Handler"
                return user, error
            print("DataSource.initializeUser() 2")
            if not self.Provider.initializeUser(name):
                error = "ERROR: No authorization for User: %s" % name
                return user, error
            print("DataSource.initializeUser() 3")
            user = self._selectUser(name)
            if not user.IsPresent:
                print("DataSource.initializeUser() 4")
                if self.Provider.isOnLine():
                    user = self._getUser(name)
                    if not user.IsPresent:
                        error = "ERROR: Can't retrieve User: %s from provider" % name
                else:
                    error = "ERROR: Can't retrieve User: %s from provider network is OffLine" % name
            print("DataSource.initializeUser() FIN")
            return user.Value, error
        except Exception as e:
            print("DataSource.initializeUser().Error: %s - %s" % (e, traceback.print_exc()))

    def _getContentType(self):
        try:
            call = self._getDataSourceCall('getSetting')
            call.setString(1, 'ContentType')
            result = call.executeQuery()
            if result.next():
                folder = result.getString(1)
                link = result.getString(2)
            call.close()
            return folder, link
        except Exception as e:
            print("DataSource._getContentType().Error: %s - %s" % (e, traceback.print_exc()))

    def _selectUser(self, name):
        print("DataSource._selectUser() 1")
        user = uno.createUnoStruct('com.sun.star.beans.Optional<com.sun.star.auth.XRestKeyMap>')
        user.Value = self.Provider.Request.getKeyMap()
        select = self._getDataSourceCall('getUser')
        select.setString(1, name)
        result = select.executeQuery()
        if result.next():
            user.IsPresent = True
            print("DataSource._selectUser() 2")
            user.Value = getKeyMapFromResult(result, self.Provider.Request.getKeyMap())
        select.close()
        print("DataSource._selectUser() 3")
        return user

    def _getUser(self, name):
        user = self.Provider.getUser(name)
        if user.IsPresent:
            root = self.Provider.getRoot(user.Value)
            if root.IsPresent:
                return self._insertUser(user.Value, root.Value)
        return user

    def _insertUser(self, user, root):
        userid = self.Provider.getUserId(user)
        username = self.Provider.getUserName(user)
        displayname = self.Provider.getUserDisplayName(user)
        rootid = self.Provider.getRootId(root)
        timestamp = parseDateTime()
        print("DataSource._insertUser() 1 %s - %s - %s - %s" % (userid, username, displayname, rootid))
        insert = self._getDataSourceCall('insertUser')
        insert.setString(1, username)
        insert.setString(2, displayname)
        insert.setString(3, rootid)
        insert.setTimestamp(4, timestamp)
        insert.setString(5, userid)
        insert.execute()
        insert.close()
        if not self._executeRootCall('update', userid, root, timestamp):
            self._executeRootCall('insert', userid, root, timestamp)
        user = uno.createUnoStruct('com.sun.star.beans.Optional<com.sun.star.auth.XRestKeyMap>')
        user.IsPresent = True
        user.Value = self.Provider.Request.getKeyMap()
        user.Value.insertValue('UserId', userid)
        user.Value.insertValue('RootId', rootid)
        user.Value.insertValue('RootName', self.Provider.getRootTitle(root))
        print("DataSource._insertUser() 2")
        return user

    def _executeRootCall(self, method, userid, root, timestamp):
        row = 0
        id = self.Provider.getRootId(root)
        call = self._getDataSourceCall('%sItem' % method)
        call.setString(1, self.Provider.getRootTitle(root))
        call.setTimestamp(2, self.Provider.getRootCreated(root, timestamp))
        call.setTimestamp(3, self.Provider.getRootModified(root, timestamp))
        call.setString(4, self.Provider.getRootMediaType(root))
        call.setLong(5, self.Provider.getRootSize(root))
        call.setBoolean(6, self.Provider.getRootTrashed(root))
        call.setString(7, id)
        row = call.executeUpdate()
        call.close()
        if row:
            call = self._getDataSourceCall('%sCapability' % method)
            call.setBoolean(1, self.Provider.getRootCanAddChild(root))
            call.setBoolean(2, self.Provider.getRootCanRename(root))
            call.setBoolean(3, self.Provider.getRootIsReadOnly(root))
            call.setBoolean(4, self.Provider.getRootIsVersionable(root))
            call.setString(5, userid)
            call.setString(6, id)
            call.executeUpdate()
            call.close()
        return row

    def getItem(self, user, identifier):
        item = self._selectItem(user, identifier)
        if not item and self.Provider.isOnLine():
            data = self.Provider.getItem(user, identifier)
            if data.IsPresent:
                item = self._insertItem(user, data.Value)
        return item

    def _selectItem(self, user, identifier):
        item = None
        select = self._getDataSourceCall('getItem')
        select.setString(1, user.getValue('UserId'))
        select.setString(2, identifier.getValue('Id'))
        result = select.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result, self.Provider.Request.getKeyMap())
        select.close()
        return item

    def _insertItem(self, user, item):
        timestamp = parseDateTime()
        rootid = user.getValue('RootId')
        c1 = self._getDataSourceCall('deleteParent')
        c2 = self._getDataSourceCall('insertParent')
        if not self._prepareItemCall('update', c1, c2, user, item, timestamp):
            self._prepareItemCall('insert', c1, c2, user, item, timestamp)
        c1.close()
        c2.close()
        id = self.Provider.getItemId(item)
        identifier = self.Provider.Request.getKeyMap()
        identifier.insertValue('Id', id)
        return self._selectItem(user, identifier)

    def _prepareItemCall(self, method, delete, insert, user, item, timestamp):
        row = 0
        userid = user.getValue('UserId')
        rootid = user.getValue('RootId')
        c1 = self._getDataSourceCall('%sItem' % method)
        c2 = self._getDataSourceCall('%sCapability' % method)
        row = self._executeItemCall(c1, c2, delete, insert, userid, rootid, item, timestamp)
        c1.close()
        c2.close()
        return row

    def _executeItemCall(self, c1, c2, c3, c4, userid, rootid, item, timestamp):
        row = 0
        id = self.Provider.getItemId(item)
        c1.setString(1, self.Provider.getItemTitle(item))
        c1.setTimestamp(2, self.Provider.getItemCreated(item, timestamp))
        c1.setTimestamp(3, self.Provider.getItemModified(item, timestamp))
        c1.setString(4, self.Provider.getItemMediaType(item))
        c1.setLong(5, self.Provider.getItemSize(item))
        c1.setBoolean(6, self.Provider.getItemTrashed(item))
        c1.setString(7, id)
        row = c1.executeUpdate()
        if row:
            c2.setBoolean(1, self.Provider.getItemCanAddChild(item))
            c2.setBoolean(2, self.Provider.getItemCanRename(item))
            c2.setBoolean(3, self.Provider.getItemIsReadOnly(item))
            c2.setBoolean(4, self.Provider.getItemIsVersionable(item))
            c2.setString(5, userid)
            c2.setString(6, id)
            c2.executeUpdate()
            c3.setString(1, userid)
            c3.setString(2, id)
            c3.executeUpdate()
            c4.setString(1, userid)
            c4.setString(2, id)
            for parent in self.Provider.getItemParent(item, rootid):
                c4.setString(3, parent)
                c4.executeUpdate()
        return row

    def getFolderContent(self, user, identifier, content, updated):
        if ONLINE == content.getValue('Loaded') == self.Provider.SessionMode:
            updated = self._updateFolderContent(user, content)
        select = self._getChildren(user, identifier)
        return select, updated

    def _updateFolderContent(self, user, content):
        updated = []
        c1 = self._getDataSourceCall('updateItem')
        c2 = self._getDataSourceCall('updateCapability')
        c3 = self._getDataSourceCall('insertItem')
        c4 = self._getDataSourceCall('insertCapability')
        c5 = self._getDataSourceCall('deleteParent')
        c6 = self._getDataSourceCall('insertParent')
        userid = user.getValue('UserId')
        rootid = user.getValue('RootId')
        timestamp = parseDateTime()
        enumerator = self.Provider.getFolderContent(content)
        while enumerator.hasMoreElements():
            item = enumerator.nextElement()
            updated.append(self._mergeItem(c1, c2, c3, c4, c5, c6, userid, rootid, item, timestamp))
        c1.close()
        c2.close()
        c3.close()
        c4.close()
        c5.close()
        c6.close()
        return all(updated)

    def _mergeItem(self, c1, c2, c3, c4, c5, c6, userid, rootid, item, timestamp):
        row = self._executeItemCall(c1, c2, c5, c6, userid, rootid, item, timestamp)
        if not row:
            row = self._executeItemCall(c3, c4, c5, c6, userid, rootid, item, timestamp)
        return row

    def _getChildren(self, user, identifier):
        select = self._getDataSourceCall('getChildren')
        scroll = 'com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE'
        select.ResultSetType = uno.getConstantByName(scroll)
        # OpenOffice / LibreOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #     'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # "TargetURL" is done by CONCAT(BaseURL,'/',Title or Id)...
        url = identifier.getValue('BaseURL')
        select.setString(1, url)
        select.setString(2, url)
        select.setString(3, user.getValue('UserId'))
        select.setString(4, identifier.getValue('Id'))
        select.setShort(5, self.Provider.SessionMode)
        return select

    def checkNewIdentifier(self, user):
        if self.Provider.isOffLine() or not self.Provider.GenerateIds:
            return
        result = False
        if self._countIdentifier(user) < min(self.Provider.IdentifierRange):
            result = self._insertIdentifier(user)
        print("DataSource.checkNewIdentifier() %s" % result)
        return
    def getNewIdentifier(self, user):
        if self.Provider.GenerateIds:
            id = ''
            select = self._getDataSourceCall('getNewIdentifier')
            select.setString(1, user.getValue('UserId'))
            result = select.executeQuery()
            if result.next():
                id = result.getString(1)
            select.close()
        else:
            id = binascii.hexlify(uno.generateUuid().value).decode('utf-8')
        print("DataSource.getNewIdentifier() %s" % id)
        return id

    def _countIdentifier(self, user):
        count = 0
        call = self._getDataSourceCall('countNewIdentifier')
        call.setString(1, user.getValue('UserId'))
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count
    def _insertIdentifier(self, user):
        result = []
        enumerator = self.Provider.getIdentifier(user)
        insert = self._getDataSourceCall('insertIdentifier')
        insert.setString(1, user.getValue('UserId'))
        while enumerator.hasMoreElements():
            result.append(self._doInsert(insert, enumerator.nextElement()))
        insert.close()
        print("DataSource._insertIdentifier() %s" % len(result))
        return all(result)
    def _doInsert(self, insert, id):
        insert.setString(2, id)
        return insert.executeUpdate()

    def synchronize(self, user, value):
        print("DataSource.synchronize(): 1")
        if self.Provider.isOffLine() or value is None:
            return value
        print("DataSource.synchronize(): 2")
        results = []
        uploader = self.Provider.getUploader(self)
        for item in self._getItemToSync(user):
            print("DataSource.synchronize(): 3")
            response = self._syncItem(uploader, item)
            print("DataSource.synchronize(): 4")
            if response is None:
                continue
            elif response and response.IsPresent:
                results.append(self._updateSync(item, response.Value))
            else:
                print("DataSource.synchronize(): all -> Error")
                continue
            print("DataSource.synchronize(): all -> Ok")
        return value if all(results) else None

    def _getItemToSync(self, user):
        items = []
        select = self._getDataSourceCall('getItemToSync')
        select.setString(1, user.getValue('UserId'))
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result, user, self.Provider))
        select.close()
        return items

    def _syncItem(self, uploader, item):
        try:
            print("DataSource._syncItem(): 1")
            response = False
            mode = item.getValue('Mode')
            print("DataSource._syncItem(): 2 %s" % mode)
            if mode == SYNC_FOLDER:
                response = self.Provider.createFolder(item)
            elif mode == SYNC_FILE:
                response = self.Provider.createFile(uploader, item)
            elif mode == SYNC_CREATED:
                response = self.Provider.uploadFile(uploader, item, True)
            elif mode == SYNC_REWRITED:
                print("DataSource._syncItem(): 3")
                response = self.Provider.uploadFile(uploader, item, False)
            elif mode == SYNC_RENAMED:
                response = self.Provider.updateTitle(item)
            elif mode == SYNC_TRASHED:
                response = self.Provider.updateTrashed(item)
            return response
        except Exception as e:
            print("DataSource._syncItem().Error: %s - %s" % (e, traceback.print_exc()))

    def callBack(self, item, response):
        if response.IsPresent:
            self._updateSync(item, response.Value)

    def _updateSync(self, item, response):
        oldid = item.getValue('Id')
        newid = self.Provider.getResponseId(response, oldid)
        oldname = item.getValue('Title')
        newname = self.Provider.getResponseTitle(response, oldname)
        delete = self._getDataSourceCall('deleteSyncMode')
        delete.setLong(1, item.getValue('SyncId'))
        row = delete.executeUpdate()
        delete.close()
        if row and newid != oldid:
            update = self._getDataSourceCall('updateItemId')
            update.setString(1, newid)
            update.setString(2, oldid)
            row = update.executeUpdate()
            update.close()
        print("DataSource._updateSync() %s - %s - %s - %s" % (oldid, newid, oldname, newname))
        return '' if row != 1 else newid

    def insertNewDocument(self, userid, itemid, parentid, content):
        if self.Provider.TwoStepCreation:
            modes = (SYNC_CREATED, SYNC_REWRITED)
        else:
            modes = (SYNC_FILE, )
        return self._insertNewContent(userid, itemid, parentid, content, modes)
    def insertNewFolder(self, userid, itemid, parentid, content):
        modes = (SYNC_FOLDER, )
        return self._insertNewContent(userid, itemid, parentid, content, modes)

    def _insertNewContent(self, userid, itemid, parentid, content, modes):
        print("DataSource._insertNewContent() %s - %s" % (itemid, content.getValue('Title')))
        c1 = self._getDataSourceCall('insertItem')
        c1.setString(1, content.getValue("Title"))
        c1.setTimestamp(2, content.getValue('DateCreated'))
        c1.setTimestamp(3, content.getValue('DateModified'))
        c1.setString(4, content.getValue('MediaType'))
        c1.setLong(5, content.getValue('Size'))
        c1.setBoolean(6, content.getValue('Trashed'))
        c1.setString(7, itemid)
        row = c1.executeUpdate()
        c1.close()
        c2 = self._getDataSourceCall('insertCapability')
        c2.setBoolean(1, content.getValue('CanAddChild'))
        c2.setBoolean(2, content.getValue('CanRename'))
        c2.setBoolean(3, content.getValue('IsReadOnly'))
        c2.setBoolean(4, content.getValue('IsVersionable'))
        c2.setString(5, userid)
        c2.setString(6, itemid)
        row += c2.executeUpdate()
        c2.close()
        c3 = self._getDataSourceCall('insertParent')
        c3.setString(1, userid)
        c3.setString(2, itemid)
        c3.setString(3, parentid)
        row += c3.executeUpdate()
        c3.close()
        c4 = self._getDataSourceCall('insertSyncMode')
        c4.setString(1, userid)
        c4.setString(2, itemid)
        c4.setString(3, parentid)
        for mode in modes:
            c4.setLong(4, mode)
            row += c4.execute()
        c4.close()
        print("DataSource._insertNewContent() %s" % row)
        return row == 3 + len(modes)

    def updateLoaded(self, userid, itemid, value, default):
        update = self._getDataSourceCall('updateLoaded')
        update.setLong(1, value)
        update.setString(2, itemid)
        row = update.executeUpdate()
        update.close()
        return default if row != 1 else value

    def updateTitle(self, userid, itemid, parentid, value, default):
        row = 0
        update = self._getDataSourceCall('updateTitle')
        update.setString(1, value)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_RENAMED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        return default if row != 1 else value

    def updateSize(self, userid, itemid, parentid, size):
        row = 0
        update = self._getDataSourceCall('updateSize')
        update.setLong(1, size)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_REWRITED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        print("DataSource.updateSize() FIN")
        return None if row != 1 else size

    def updateTrashed(self, userid, itemid, parentid, value, default):
        row = 0
        update = self._getDataSourceCall('updateTrashed')
        update.setLong(1, value)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_TRASHED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        return default if row != 1 else value

    def isChildId(self, userid, itemid, title):
        ischild = False
        call = self._getDataSourceCall('isChildId')
        call.setString(1, userid)
        call.setString(2, itemid)
        call.setString(3, title)
        result = call.executeQuery()
        if result.next():
            ischild = result.getBoolean(1)
        call.close()
        return ischild

    def countChildTitle(self, userid, parent, title):
        count = 1
        call = self._getDataSourceCall('countChildTitle')
        call.setString(1, userid)
        call.setString(2, parent)
        call.setString(3, title)
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count

    # User.initializeIdentifier() helper
    def selectChildId(self, userid, parent, basename):
        id = ''
        call = self._getDataSourceCall('getChildId')
        call.setString(1, userid)
        call.setString(2, parent)
        call.setString(3, basename)
        result = call.executeQuery()
        if result.next():
            id = result.getString(1)
        call.close()
        return id

    # User.initializeIdentifier() helper
    def isIdentifier(self, userid, id):
        isit = False
        call = self._getDataSourceCall('isIdentifier')
        call.setString(1, id)
        result = call.executeQuery()
        if result.next():
            isit = result.getBoolean(1)
        call.close()
        return isit

    def _getDataSourceCall(self, name, cache=False):
        if name in self._Calls:
            return self._Calls[name]
        query = getSqlQuery(name)
        call = self.Connection.prepareCall(query)
        if cache:
            self._Calls[name] = call
        return call
