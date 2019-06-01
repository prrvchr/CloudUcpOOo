#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb import XRestDataSource
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RETRIEVED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_CREATED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FOLDER
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FILE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RENAMED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_REWRITED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_TRASHED

# oauth2 is only available after OAuth2OOo as been loaded...
try:
    from oauth2 import KeyMap
    from oauth2 import OutputStream
except ImportError:
    print("DataSource IMPORT ERROR ******************************************************")
    pass
from .user import User

from .datasourcehelper import getDataSourceConnection
from .datasourcehelper import getDataSourceInfo
from .datasourcehelper import getKeyMapFromResult
from .datasourcehelper import setUserData
from .datasourcehelper import setRootData
from .datasourcehelper import setItemData
from .datasourcehelper import setItemParent
from .datasourcehelper import setContentData

import binascii
import traceback


class DataSource(unohelper.Base,
                 XRestDataSource):
    def __init__(self, ctx, scheme, plugin, shutdown=False):
        self.ctx = ctx
        self.Provider = None
        self._Statement = None
        self._CahedUser = {}
        self._Error = ''
        url, info = getDataSourceInfo(self.ctx, scheme, plugin, shutdown)
        connection = getDataSourceConnection(self.ctx, url, info)
        if not connection:
            self._Error = "ERROR: Can't connect to DataSource at Url: %s" % url
        else:
            # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
            self._Statement = connection.createStatement()
            print("DataSource.__init__() 1")
            service = '%s.Provider' % plugin
            self.Provider = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
            print("DataSource.__init__() 2")
            link, folder = self._getMediaType()
            print("DataSource.__init__() 3")
            self.Provider.initialize(scheme, plugin, link, folder)
            print("DataSource.__init__() 4")

    # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
    @property
    def Connection(self):
        return self._Statement.getConnection()
    @property
    def IsValid(self):
        return not self.Error
    @property
    def Error(self):
        return self.Provider.Error if self.Provider else self._Error

    def shutdownConnection(self, compact=False):
        if not self.Connection:
            self._Error = "ERROR: Can't close DataSource"
        elif self.Connection.isClosed():
            self._Error = "ERROR: DataSource at Url: %s already closed..." % self.Url
        else:
            statement = 'SHUTDOWN COMPACT;' if compact else 'SHUTDOWN;'
            self._Statement.execute(statement)
            return True
        return False

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
        print("DataSource.initializeUser() 1")
        user = KeyMap()
        if not name:
            error = "ERROR: Can't retrieve a UserName from Handler"
            return user, error
        print("DataSource.initializeUser()")
        if not self.Provider.initializeUser(name):
            error = "ERROR: No authorization for User: %s" % name
            return user, error
        user = self._selectUser(name)
        if not user.IsPresent:
            if self.Provider.isOnLine():
                user = self._getUser(name)
                if not user.IsPresent:
                    error = "ERROR: Can't retrieve User: %s from provider" % name
            else:
                error = "ERROR: Can't retrieve User: %s from provider network is OffLine" % name
        return user.Value, error

    def _getMediaType(self):
        call = self.Connection.prepareCall('CALL "getMediaType"(?, ?, ?)')
        # OpenOffice doesn't support only OUT parameters
        call.setString(1, 'dummy')
        call.execute()
        link = call.getString(2)
        folder = call.getString(3)
        call.close()
        return link, folder

    def _selectUser(self, name):
        print("DataSource._selectUser() 1")
        user = uno.createUnoStruct('com.sun.star.beans.Optional<com.sun.star.auth.XRestKeyMap>')
        user.Value = KeyMap()
        select = self.Connection.prepareCall('CALL "getUser"(?)')
        select.setString(1, name)
        result = select.executeQuery()
        if result.next():
            user.IsPresent = True
            print("ProviderBase._selectUser() 2")
            user.Value = getKeyMapFromResult(result)
        select.close()
        return user

    def _getUser(self, name):
        user = self.Provider.getUser(name)
        if user.IsPresent:
            root = self.Provider.getRoot(user.Value)
            if root.IsPresent:
                return self._mergeUser(user, root)
        return user

    def _mergeUser(self, user, root):
        timestamp = self.Provider.getTimeStamp()
        call = 'CALL "mergeUserAndRoot"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        merge = self.Connection.prepareCall(call)
        i = setUserData(self.Provider, merge, user.Value, 1)
        i = setRootData(self.Provider, merge, root.Value, timestamp, i)
        result = merge.executeQuery()
        if result.next():
            user.Value = getKeyMapFromResult(result)
        else:
            user.IsPresent = False
        merge.close()
        return user

    def getItem(self, user, identifier):
        item = self._selectItem(user, identifier)
        if not item and self.Provider.isOnLine():
            data = self.Provider.getItem(user, identifier)
            if data.IsPresent:
                item = self._insertItem(user, data.Value)
        return item

    def _selectItem(self, user, identifier):
        item = None
        select = self.Connection.prepareCall('CALL "getItem"(?, ?)')
        select.setString(1, user.getValue('UserId'))
        select.setString(2, identifier.getValue('Id'))
        result = select.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        select.close()
        return item

    def _insertItem(self, user, item):
        result = False
        timestamp = self.Provider.getTimeStamp()
        rootid = user.getValue('RootId')
        call = 'CALL "insertJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        merge = self.Connection.prepareCall(call)
        merge.setString(1, user.getValue('UserId'))
        i = setItemData(self.Provider, merge, item, timestamp, 2)
        i = setItemParent(self.Provider,merge, item, rootid, i)
        result = merge.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        merge.close()
        return item

    def getFolderContent(self, user, identifier, content, index, updated):
        if ONLINE == content.getValue('Loaded') == self.Provider.SessionMode:
            updated = self._updateFolderContent(user, content)
        select, index = self._getChildSelect(user, identifier, index)
        return select, index, updated

    def _updateFolderContent(self, user, content):
        updated = []
        timestamp = self.Provider.getTimeStamp()
        rootid = user.getValue('RootId')
        call = 'CALL "mergeJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        merge = self.Connection.prepareCall(call)
        merge.setString(1, user.getValue('UserId'))
        enumerator = self.Provider.getFolderContent(content)
        while enumerator.hasMoreElements():
            item = enumerator.nextElement()
            updated.append(self._mergeItem(merge, item, rootid, timestamp, 2))
        merge.close()
        return all(updated)

    def _mergeItem(self, merge, item, rootid, timestamp, i):
        result = 0
        i = setItemData(self.Provider, merge, item, timestamp, i)
        i = setItemParent(self.Provider, merge, item, rootid, i)
        merge.execute()
        return merge.getLong(i)

    def _getChildSelect(self, user, identifier, i=1):
        id = identifier.getValue('Id')
        select = self.Connection.prepareCall('CALL "getChildren"(?, ?, ?, ?, ?)')
        # LibreOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #     'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # OpenOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #     'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # select return RowCount as OUT parameter in select.getLong(i)!!!
        # Never managed to run the next line:
        # select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
        # selectChild(IN USERID VARCHAR(100),IN ITEMID VARCHAR(100),IN URL VARCHAR(250),IN MODE SMALLINT,OUT ROWCOUNT SMALLINT)
        select.setString(i, user.getValue('UserId'))
        i += 1
        select.setString(i, id)
        i += 1
        # "TargetURL" is done by CONCAT(BaseURL,'/',Title or Id)...
        select.setString(i, identifier.getValue('BaseURL'))
        i += 1
        select.setLong(i, self.Provider.SessionMode)
        i += 1
        return select, i

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
            select = self.Connection.prepareCall('CALL "selectIdentifier"(?)')
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
        call = self.Connection.prepareCall('CALL "countIdentifier"(?)')
        call.setString(1, user.getValue('UserId'))
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count
    def _insertIdentifier(self, user):
        result = []
        enumerator = self.Provider.getIdentifier(user)
        insert = self.Connection.prepareCall('CALL "insertIdentifier"(?, ?, ?)')
        insert.setString(1, user.getValue('UserId'))
        while enumerator.hasMoreElements():
            result.append(self._doInsert(insert, enumerator.nextElement()))
        insert.close()
        print("DataSource._insertIdentifier() %s" % len(result))
        return all(result)
    def _doInsert(self, insert, id):
        insert.setString(2, id)
        insert.execute()
        return insert.getLong(3)

    def synchronize(self, user, value):
        print("DataSource.synchronize(): 1")
        if self.Provider.isOffLine() or value is None:
            return value
        print("DataSource.synchronize(): 2")
        results = []
        uploader = self.Provider.getUploader(self.Connection)
        call, i = self._getUpdateSync(user)
        for item in self._getItemToSync(user):
            print("DataSource.synchronize(): 3")
            response = self._syncItem(item, uploader, call, i)
            print("DataSource.synchronize(): 4")
            if response is None:
                continue
            elif response and response.IsPresent:
                results.append(self._updateSync(item, response.Value, call, i))
            else:
                print("DataSource.synchronize(): all -> Error")
                continue
            print("DataSource.synchronize(): all -> Ok")
        call.close()
        return value if all(results) else None

    def _syncItem(self, item, uploader, call, i):
        response = False
        mode = item.getValue('Mode')
        if mode & SYNC_CREATED:
            if mode & SYNC_FOLDER:
                parameter = self.Provider.getUpdateParameter(item, True, '')
                response = self.Provider.updateContent(parameter)
            if mode & SYNC_FILE:
                parameter = self.Provider.getUploadParameter(item, True)
                response = None if uploader.start(item, parameter) else False
        else:
            if mode & SYNC_REWRITED:
                parameter = self.Provider.getUploadParameter(item, False)
                response = None if uploader.start(item, parameter) else False
            if mode & SYNC_RENAMED:
                parameter = self.Provider.getUpdateParameter(item, False, 'Title')
                response = self.Provider.updateContent(parameter)
        if mode & SYNC_TRASHED:
            parameter = self.Provider.getUpdateParameter(item, False, 'Trashed')
            response = self.Provider.updateContent(parameter)
        return response

    def _getItemToSync(self, user):
        items = []
        select = self.Connection.prepareCall('CALL "selectSync"(?, ?)')
        select.setString(1, user.getValue('UserId'))
        select.setLong(2, SYNC_RETRIEVED)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result, user, self.Provider))
        select.close()
        return items

    def _getUpdateSync(self, user):
        call = self.Connection.prepareCall('CALL "updateSync"(?, ?, ?, ?, ?, ?, ?)')
        call.setString(1, user.getValue('UserId'))
        call.setLong(2, SYNC_RETRIEVED)
        return call, 3

    def _updateSync(self, item, response, call, i):
        oldid = self.Provider.getItemId(item)
        newid = self.Provider.getResponseId(response, item)
        oldname = self.Provider.getItemName(item)
        newname = self.Provider.getResponseName(response, item)
        call.setString(i, oldid)
        i += 1
        call.setString(i, newid)
        i += 1
        call.setString(i, oldname)
        i += 1
        call.setString(i, newname)
        i += 1
        call.execute()
        error = call.getString(i)
        print("DataSource._updateSync() %s - %s - %s - %s" % (oldid, newid, oldname, newname))
        return '' if error != '' else id

    def insertNewDocument(self, userid, itemid, parentid, content):
        mode = SYNC_CREATED | SYNC_FILE
        return self._insertContent(userid, itemid, parentid, content, mode)
    def insertNewFolder(self, userid, itemid, parentid, content):
        mode = SYNC_CREATED | SYNC_FOLDER
        return self._insertContent(userid, itemid, parentid, content, mode)

    def _insertContent(self, userid, itemid, parentid, content, mode):
        call = 'CALL "insertNewContent"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        print("items.insertContentItem() %s - %s" % (itemid, content.getValue('Title')))
        insert = self.Connection.prepareCall(call)
        insert.setString(1, userid)
        insert.setString(2, itemid)
        insert.setLong(3, mode)
        insert.setString(4, parentid)
        index = setContentData(insert, content, 5)
        insert.execute()
        result = insert.getLong(index)
        insert.close()
        print("items.insertContentItem() %s" % result)
        return result == 1

    def updateLoaded(self, userid, itemid, value, default):
        update = self.Connection.prepareCall('CALL "updateLoaded"(?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, itemid)
        update.setLong(3, value)
        update.execute()
        result = update.getLong(4)
        update.close()
        return default if result != 1 else value

    def updateTitle(self, userid, itemid, value, default):
        update = self.Connection.prepareCall('CALL "updateTitle"(?, ?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, itemid)
        update.setString(3, value)
        update.setLong(4, SYNC_RENAMED)
        update.execute()
        result = update.getLong(5)
        update.close()
        return default if result != 1 else value

    def updateSize(self, userid, itemid, size):
        update = self.Connection.prepareCall('CALL "updateSize"(?, ?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, itemid)
        update.setLong(3, size)
        update.setLong(4, SYNC_REWRITED)
        update.execute()
        result = update.getLong(5)
        update.close()
        print("DataSource.updateSize() FIN")
        return None if result != 1 else size

    def updateTrashed(self, userid, itemid, value, default):
        update = self.Connection.prepareCall('CALL "updateTrashed"(?, ?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, itemid)
        update.setLong(3, value)
        update.setLong(4, SYNC_TRASHED)
        update.execute()
        result = update.getLong(5)
        update.close()
        return default if result != 1 else value

    def isChildId(self, userid, itemid, title):
        ischild = False
        call = self.Connection.prepareCall('CALL "isChildId"(?, ?)')
        call.setString(1, itemid)
        call.setString(2, title)
        result = call.executeQuery()
        if result.next():
            ischild = result.getBoolean(1)
        call.close()
        return ischild

    def countChildTitle(self, userid, parent, title):
        count = 1
        call = self.Connection.prepareCall('CALL "countChildTitle"(?, ?, ?)')
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
        call = self.Connection.prepareCall('CALL "selectChildId"(?, ?, ?)')
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
        count = 0
        call = self.Connection.prepareCall('CALL "isIdentifier"(?, ?)')
        call.setString(1, userid)
        call.setString(2, id)
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count > 0
