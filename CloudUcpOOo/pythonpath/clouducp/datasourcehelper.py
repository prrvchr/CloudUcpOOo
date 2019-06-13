#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.sdbc import SQLException
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RETRIEVED

# oauth2 is only available after OAuth2OOo as been loaded...
try:
    from oauth2 import KeyMap
except ImportError:
    print("DataSourceHelper IMPORT ERROR ******************************************************")
    pass

from .unotools import getPropertyValue
from .unotools import getResourceLocation
from .unotools import getSimpleFile
from .unotools import getPropertyValue
from .unotools import getConfiguration
from .configuration import g_identifier
from .configuration import g_protocol
from .configuration import g_folder
from .configuration import g_jar
from .configuration import g_class
from .configuration import g_options
from .configuration import g_shutdow

import traceback


def getDataSourceUrl(ctx, scheme, plugin):
    try:
        path = getResourceLocation(ctx, plugin, g_folder)
        url = '%s/%s.odb' % (path, scheme)
        print("DataSourceHelper.getDataSourceUrl() 1: %s" % url)
        if not getSimpleFile(ctx).exists(url):
            _createDataSource(ctx, scheme, path, url)
        print("DataSourceHelper.getDataSourceUrl() FIN")
        return url
    except Exception as e:
        print("DataSourceHelper.getDataSourceUrl().Error: %s - %s" % (e, traceback.print_exc()))

def getDataSourceConnection(ctx, url):
    print("DataSourceHelper.getDataSource() 1")
    connection = None
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    try:
        datasource = dbcontext.getByName(url)
        print("DataSourceHelper.getDataSource() 2")
        connection = datasource.getIsolatedConnection('', '')
    except Exception as e:
        pass
    print("DataSourceHelper.getDataSource() FIN")
    return connection

def _createDataSource(ctx, scheme, path, url):
    try:
        dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
        print("DataSourceHelper._createDataSource() 1")
        datasource = dbcontext.createInstance()
        datasource.URL = _getDataSourceUrl(scheme, path, False)
        info = (getPropertyValue('JavaDriverClass', g_class),
                getPropertyValue('JavaDriverClassPath', '%s/%s' % (path, g_jar)))
        datasource.Info = info
        datasource.DatabaseDocument.storeAsURL(url, ())
        #odb = datasource.DatabaseDocument
        print("DataSourceHelper._createDataSource() 2")
        _createDataBase(datasource, scheme)
        print("DataSourceHelper._createDataSource() 3")
        #datasource.DatabaseDocument.storeAsURL(url, ())
        print("DataSourceHelper._createDataSource() 4")
        datasource.DatabaseDocument.store()
        print("DataSourceHelper._createDataSource() FIN")
    except Exception as e:
        print("DataSourceHelper._createDataSource().Error: %s - %s" % (e, traceback.print_exc()))

def _createDataBase(datasource, scheme):
    print("DataSourceHelper._createDataBase() 1")
    connection = datasource.getConnection('', '')
    statement = connection.createStatement()
    statement.executeQuery(getSqlQuery('createSettingsTable'))
    statement.executeQuery(getSqlQuery('setSettingsSource') %  scheme)
    statement.executeQuery(getSqlQuery('setSettingsReadOnly'))
    statement.executeQuery(getSqlQuery('createUsersTable'))
    statement.executeQuery(getSqlQuery('createItemsTable'))
    statement.executeQuery(getSqlQuery('createParentsTable'))
    statement.executeQuery(getSqlQuery('createCapabilitiesTable'))
    statement.executeQuery(getSqlQuery('createIdentifiersTable'))
    statement.executeQuery(getSqlQuery('createSynchronizesTable'))
    statement.executeQuery(getSqlQuery('createItemView'))
    statement.executeQuery(getSqlQuery('createChildView'))
    statement.executeQuery(getSqlQuery('createSyncView'))
    connection.close()
    connection.dispose()
    print("DataSourceHelper._createDataBase() FIN")

def _createDataSource3(ctx, scheme, url):
    dbcontext.registerObject(scheme, datasource)
    uri = _getDataSourcePath(scheme, location, shutdown)
    print("DataSourceHelper._createDataSource() 2: %s" % uri)
    datasource.URL = uri
    datasource.Settings.JavaDriverClass = g_class
    print("DataSourceHelper._createDataSource() 3: %s" % path)
    datasource.Settings.JavaDriverClassPath = path
    #datasource.Info = _getInfo(ctx, location)
    descriptor = (getPropertyValue('Overwrite', True), )
    #mri = ctx.ServiceManager.createInstance('mytools.Mri')
    #mri.inspect(datasource)
    datasource.DatabaseDocument.storeAsURL(url, descriptor)

def getDataSourceConnection6(ctx, scheme, url):
    try:
        print("DataSourceHelper.getDataSourceConnection() 1: %s" % url)
        connection = None
        dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
        if getSimpleFile(ctx).exists(url):
            print("DataSourceHelper.getDataSourceConnection() 2")
            datasource = dbcontext.getByName(url)
            connection = datasource.getConnection('', '')
        else:
            print("DataSourceHelper.getDataSourceConnection() 3")
            connection = _createDataSource(dbcontext, scheme, url)
        print("DataSourceHelper.getDataSourceConnection() FIN")
        return connection
    except Exception as e:
        print("DataSourceHelper.getDataSourceConnection().Error: %s - %s" % (e, traceback.print_exc()))

def getDataSourceConnection3(ctx, scheme, url):
    print("DataSourceHelper.getDataSourceConnection() 1: %s" % url)
    connection = None
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if not dbcontext.hasRegisteredDatabase(scheme):
        dbcontext.registerDatabaseLocation(scheme, url)
    elif dbcontext.getDatabaseLocation(scheme) != url:
        dbcontext.changeDatabaseLocation(scheme, url)
    print("DataSourceHelper.getDataSourceConnection() 2: %s" % url)
    #mri = ctx.ServiceManager.createInstance('mytools.Mri')
    #mri.inspect(dbcontext)
    if dbcontext.hasByName(scheme):
        datasource = dbcontext.getByName(scheme)
        connection = datasource.getConnection('', '')
    print("DataSourceHelper.getDataSourceConnection() 3")
    return connection

def getDataSourceInfo(ctx, scheme, plugin, shutdown=False):
    # ToDo check if 'hsqldb.jar' is in Libre/OpenOffice 'ClassPath' and add it if not...
    location = getResourceLocation(ctx, plugin, g_folder)
    path = _getClassPath(ctx)
    info = _getInfo(path)
    #_registerDataSource(ctx, path, scheme, location, shutdown)
    #_registerJavaClass(ctx, location)
    url = _getDataSourcePath(scheme, location, shutdown)
    print("DataSourceHelper.getDataSourceUrl() 1: %s" % url)
    return url, info

def getDataSourceConnection1(ctx, scheme):
    try:
        print("DataSourceHelper.getDataSourceConnection() 1: %s" % scheme)
        dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
        datasource = dbcontext.getByName(scheme)
        #mri = ctx.ServiceManager.createInstance('mytools.Mri')
        #mri.inspect(datasource)
        connection = datasource.getConnection('', '')
        return connection
    except Exception as e:
        print("DataSourceHelper.getDataSourceConnection().Error: %s - %s" % (e, traceback.print_exc()))

def getDataSourceConnection2(ctx, url, info):
    connection = None
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    try:
        connection = pool.getConnectionWithInfo(url, info)
    except SQLException:
        pass
    return connection

def _registerDataSource(ctx, path, scheme, location, shutdown=False):
    print("DataSourceHelper._registerDataSource() 1")
    url = '%s/%s.odb' % (location, scheme)
    print("DataSourceHelper._registerDataSource() 2: %s" % url)
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if not getSimpleFile(ctx).exists(url):
        _createDataSource(ctx, dbcontext, path, scheme, location, url, shutdown)
    if not dbcontext.hasRegisteredDatabase(scheme):
        dbcontext.registerDatabaseLocation(scheme, url)
    elif dbcontext.getDatabaseLocation(scheme) != url:
        dbcontext.changeDatabaseLocation(scheme, url)
    print("DataSourceHelper._registerDataSource() 3")

def _getDataSourceUrl(scheme, url, shutdown):
    location = uno.fileUrlToSystemPath(url)
    return '%sfile:%s/%s%s%s' % (g_protocol, location, scheme, g_options, g_shutdow if shutdown else '')

def _getDataSourcePath(scheme, location, shutdown):
    path = uno.fileUrlToSystemPath(location)
    print("DataSourceHelper._getDataSourcePath() 1: %s" % path)
    return '%sfile:%s/%s%s%s' % (g_protocol, path, scheme, g_options, g_shutdow if shutdown else '')

def _getDataSourceClassPath(location):
    path = location
    print("DataSourceHelper._getDataSourceClassPath() 1: %s" % path)
    return '%s/%s' % (path, g_jar)

def getKeyMapFromResult(result, keymap=None, provider=None):
    item = KeyMap() if keymap is None else keymap
    #print("DataSource._getKetMapFromResult() %s" % result.MetaData.ColumnCount)
    for i in range(1, result.MetaData.ColumnCount +1):
        dbtype = result.MetaData.getColumnTypeName(i)
        name = result.MetaData.getColumnName(i)
        if dbtype == 'VARCHAR':
            value = result.getString(i)
        elif dbtype == 'TIMESTAMP':
            value = result.getTimestamp(i)
        elif dbtype == 'BOOLEAN':
            value = result.getBoolean(i)
        elif dbtype == 'BIGINT' or dbtype == 'SMALLINT':
            value = result.getLong(i)
        else:
            #print("DataSource._getKetMapFromResult() %s - %s" % (dbtype, name))
            continue
        #print("DataSource._getKetMapFromResult() %s - %s - %s" % (i, name, value))
        if result.wasNull():
            value = None
        if provider:
            value = provider.transform(name, value)
        item.insertValue(name, value)
    return item

def _getClassPath(ctx):
    location = getResourceLocation(ctx, g_identifier, g_jar)
    return location

def _getInfo(path):
    print("DataSourceHelper._getInfo() 1: %s" % path)
    return (getPropertyValue('JavaDriverClass', g_class),
            getPropertyValue('JavaDriverClassPath', path))

def getSqlQuery(name):
    if name == 'createSettingsTable':
        c1 = '"Setting" VARCHAR(100) NOT NULL PRIMARY KEY'
        c2 = '"Set1" VARCHAR(100) NOT NULL'
        c3 = '"Set2" VARCHAR(100) NOT NULL'
        c4 = '"Set3" VARCHAR(100) NOT NULL'
        columns = (c1, c2, c3, c4)
        query = 'CREATE TEXT TABLE "Settings"(%s)' % ','.join(columns)
    elif name == 'setSettingsSource':
        query = 'SET TABLE "Settings" SOURCE "%s.csv"'
    elif name == 'setSettingsReadOnly':
        query = 'SET TABLE "Settings" READONLY TRUE'
    elif name == 'createUsersTable':
        c1 = '"UserId" VARCHAR(100) NOT NULL'
        c2 = '"UserName" VARCHAR(100) NOT NULL'
        c3 = '"DisplayName" VARCHAR(100)'
        c4 = '"RootId" VARCHAR(100) NOT NULL'
        c5 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'PRIMARY KEY("UserId")'
        k2 = 'CONSTRAINT "UniqueUserName" UNIQUE("UserName")'
        columns = (c1, c2, c3, c4, c5, k1, k2)
        query = 'CREATE CACHED TABLE "Users"(%s)' % ','.join(columns)
    elif name == 'createItemsTable':
        c1 = '"ItemId" VARCHAR(100) NOT NULL'
        c2 = '"Title" VARCHAR(100)'
        c3 = '"DateCreated" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        c4 = '"DateModified" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        c5 = '"MediaType" VARCHAR(100) DEFAULT \'application/octet-stream\' NOT NULL'
        c6 = '"Size" BIGINT DEFAULT 0 NOT NULL'
        c7 = '"Trashed" BOOLEAN DEFAULT FALSE NOT NULL'
        c8 = '"Loaded" SMALLINT DEFAULT 0 NOT NULL'
        c9 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'PRIMARY KEY("ItemId")'
        columns = (c1, c2, c3, c4, c5, c6, c7, c8, c9, k1)
        query = 'CREATE CACHED TABLE "Items"(%s)' % ','.join(columns)
    elif name == 'createParentsTable':
        c1 = '"UserId" VARCHAR(100) NOT NULL'
        c2 = '"ItemId" VARCHAR(100) NOT NULL'
        c3 = '"ChildId" VARCHAR(100) NOT NULL'
        c4 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'PRIMARY KEY("UserId","ItemId","ChildId")'
        k2 = 'CONSTRAINT "ForeignParentUsers" FOREIGN KEY("UserId") REFERENCES "Users"("UserId") ON DELETE CASCADE ON UPDATE CASCADE'
        k3 = 'CONSTRAINT "ForeignParentItems" FOREIGN KEY("ItemId") REFERENCES "Items"("ItemId") ON DELETE CASCADE ON UPDATE CASCADE'
        k4 = 'CONSTRAINT "ForeignChildItems" FOREIGN KEY("ChildId") REFERENCES "Items"("ItemId") ON DELETE CASCADE ON UPDATE CASCADE'
        columns = (c1, c2, c3, c4, k1, k2, k3, k4)
        query = 'CREATE CACHED TABLE "Parents"(%s)' % ','.join(columns)
    elif name == 'createCapabilitiesTable':
        c1 = '"UserId" VARCHAR(100) NOT NULL'
        c2 = '"ItemId" VARCHAR(100) NOT NULL'
        c3 = '"CanAddChild" BOOLEAN DEFAULT TRUE NOT NULL'
        c4 = '"CanRename" BOOLEAN DEFAULT TRUE NOT NULL'
        c5 = '"IsReadOnly" BOOLEAN DEFAULT FALSE NOT NULL'
        c6 = '"IsVersionable" BOOLEAN DEFAULT FALSE NOT NULL'
        c7 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'PRIMARY KEY("UserId","ItemId")'
        k2 = 'CONSTRAINT "ForeignCapabilitiesUsers" FOREIGN KEY("UserId") REFERENCES "Users"("UserId") ON DELETE CASCADE ON UPDATE CASCADE'
        k3 = 'CONSTRAINT "ForeignCapabilitiesItems" FOREIGN KEY("ItemId") REFERENCES "Items"("ItemId") ON DELETE CASCADE ON UPDATE CASCADE'
        columns = (c1, c2, c3, c4, c5, c6, c7, k1, k2, k3)
        query = 'CREATE CACHED TABLE "Capabilities"(%s)' % ','.join(columns)
    elif name == 'createIdentifiersTable':
        c1 = '"Id" VARCHAR(100) NOT NULL'
        c2 = '"UserId" VARCHAR(100) NOT NULL'
        c3 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'PRIMARY KEY("Id")'
        k2 = 'CONSTRAINT "ForeignIdentifiersUsers" FOREIGN KEY("UserId") REFERENCES PUBLIC."Users"("UserId") ON DELETE CASCADE ON UPDATE CASCADE'
        columns = (c1, c2, c3, k1, k2)
        query = 'CREATE CACHED TABLE "Identifiers"(%s)' % ','.join(columns)
    elif name == 'createSynchronizesTable':
        c1 = '"SyncId" BIGINT GENERATED BY DEFAULT AS IDENTITY'
        c2 = '"UserId" VARCHAR(100) NOT NULL'
        c3 = '"ItemId" VARCHAR(100) NOT NULL'
        c4 = '"ParentId" VARCHAR(100) NOT NULL'
        c5 = '"SyncMode" SMALLINT DEFAULT 0 NOT NULL'
        c6 = '"TimeStamp" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP NOT NULL'
        k1 = 'CONSTRAINT "ForeignSynchronizesUsers" FOREIGN KEY("UserId") REFERENCES "Users"("UserId") ON DELETE CASCADE ON UPDATE CASCADE'
        k2 = 'CONSTRAINT "ForeignSynchronizesItems" FOREIGN KEY("ItemId") REFERENCES "Items"("ItemId") ON DELETE CASCADE ON UPDATE CASCADE'
        columns = (c1, c2, c3, c4, c5, c6, k1, k2)
        query = 'CREATE CACHED TABLE "Synchronizes"(%s)' % ','.join(columns)
    elif name == 'createItemView':
        c1 = '"UserId","ItemId","Title","DateCreated","DateModified","ContentType","MediaType","IsFolder","IsLink","IsDocument","Size","Trashed","Loaded","CanAddChild","CanRename","IsReadOnly","IsVersionable","IsRoot","RootId"'
        c2 = '"U"."UserId","I"."ItemId","I"."Title","I"."DateCreated","I"."DateModified",CASE WHEN "I"."MediaType" IN ("S"."Set2","S"."Set3") THEN "I"."MediaType" ELSE "S"."Set1" END,"I"."MediaType","I"."MediaType"="S"."Set2","I"."MediaType"="S"."Set3","I"."MediaType"!="S"."Set2" AND "I"."MediaType"!="S"."Set3","I"."Size","I"."Trashed","I"."Loaded","C"."CanAddChild","C"."CanRename","C"."IsReadOnly","C"."IsVersionable","I"."ItemId"="U"."RootId","U"."RootId" FROM "Settings" AS "S","Items" AS "I" JOIN "Capabilities" AS "C" ON "I"."ItemId"="C"."ItemId" JOIN "Users" AS "U" ON "C"."UserId"="U"."UserId" WHERE "S"."Setting"=\'ContentType\''
        query = 'CREATE VIEW "Item" (%s) AS SELECT %s' % (c1, c2)
    elif name == 'createChildView':
        c1 = '"UserId","ItemId","ParentId","Title","DateCreated","DateModified","IsFolder","Size","IsHidden","IsVolume","IsRemote","IsRemoveable","IsFloppy","IsCompactDisc","Loaded"'
        c2 = '"I"."UserId","I"."ItemId","P"."ItemId","I"."Title","I"."DateCreated","I"."DateModified","I"."IsFolder","I"."Size",FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,"I"."Loaded" FROM "Item" AS "I" JOIN "Parents" AS "P" ON "I"."ItemId"="P"."ChildId" AND "I"."UserId"="P"."UserId"'
        query = 'CREATE VIEW "Child" (%s) AS SELECT %s' % (c1, c2)
    elif name == 'createSyncView':
        c1 = '"SyncId","UserId","Id","ParentId","Title","DateCreated","DateModified","MediaType","IsFolder","Size","Trashed","Mode","IsRoot","AtRoot"'
        c2 = '"S"."SyncId","S"."UserId","S"."ItemId","S"."ParentId","I"."Title","I"."DateCreated","I"."DateModified","I"."MediaType","I"."IsFolder","I"."Size","I"."Trashed","S"."SyncMode","I"."IsRoot","S"."ParentId"="I"."RootId" FROM "Synchronizes" AS "S" JOIN "Item" AS "I" ON "S"."ItemId"="I"."ItemId" AND "S"."UserId"="I"."UserId"'
        query = 'CREATE VIEW "Sync" (%s) AS SELECT %s' % (c1, c2)
    elif name == 'getSetting':
        query = 'SELECT "Set2", "Set3" FROM "Settings" WHERE "Setting" = ?'
    elif name == 'getUser':
        query = 'SELECT "U"."UserId", "U"."RootId", "I"."Title" "RootName" FROM "Users" "U" JOIN "Items" "I" ON "U"."RootId" = "I"."ItemId" WHERE "U"."UserName" = ?'
    elif name == 'getItem':
        query = 'SELECT "ItemId" "Id", "Title", "Title" "TitleOnServer", "DateCreated", "DateModified", "ContentType", "MediaType", "Size", "Trashed", "IsRoot", "IsFolder", "IsDocument", "CanAddChild", "CanRename", "IsReadOnly", "IsVersionable", "Loaded", \'\' "CasePreservingURL", FALSE "IsHidden", FALSE "IsVolume", FALSE "IsRemote", FALSE "IsRemoveable", FALSE "IsFloppy", FALSE "IsCompactDisc" FROM "Item" WHERE "UserId" = ? AND "ItemId" = ?'
    elif name == 'getChildren':
        query = 'SELECT "Title", "Size", "DateModified", "DateCreated", "IsFolder", CASE WHEN "IsFolder" = TRUE THEN CONCAT( ?, CONCAT( \'/\', "ItemId" ) ) ELSE CONCAT( ?, CONCAT( \'/\', "Title" ) ) END "TargetURL", "IsHidden", "IsVolume", "IsRemote", "IsRemoveable", "IsFloppy", "IsCompactDisc" FROM "Child" WHERE "UserId" = ? AND "ParentId" = ? AND ( "IsFolder" = TRUE OR "Loaded" >= ? )'
    elif name == 'getChildId':
        query = 'SELECT "ItemId" FROM "Child" WHERE "UserId" = ? AND "ParentId" = ? AND "Title" = ?'
    elif name == 'getNewIdentifier':
        query = 'SELECT "Id" FROM "Identifiers" WHERE "UserId" = ? ORDER BY "TimeStamp" LIMIT 1'
    elif name == 'countNewIdentifier':
        query = 'SELECT COUNT( "Id" ) "Id" FROM "Identifiers" WHERE "UserId" = ?'
    elif name == 'countChildTitle':
        query = 'SELECT COUNT( "Title" ) FROM "Child" WHERE "UserId" = ? AND "ParentId" = ? AND "Title" = ?'
    elif name == 'isChildId':
        query = 'SELECT CAST( COUNT( 1 ) AS "BOOLEAN" ) "IsChild" FROM "Parents" WHERE "UserId" = ? AND "ChildId" = ? AND "ItemId" = ?'
    elif name == 'isIdentifier':
        query = 'SELECT CAST( COUNT( 1 ) AS "BOOLEAN" ) "IsIdentifier" FROM "Items" WHERE "ItemId" = ?'
    elif name == 'getItemToSync':
        query = 'SELECT * FROM "Sync" WHERE "UserId" = ? ORDER BY "SyncId"'
    elif name == 'insertUser':
        columns = '"UserName","DisplayName","RootId","TimeStamp","UserId"'
        query = 'INSERT INTO "Users" (%s) VALUES (?,?,?,?,?)' % columns
    elif name == 'insertItem':
        columns = '"Title","DateCreated","DateModified","MediaType","Size","Trashed","ItemId"'
        query = 'INSERT INTO "Items" (%s) VALUES (?,?,?,?,?,?,?)' % columns
    elif name == 'updateItem':
        columns = '"Title"=?,"DateCreated"=?,"DateModified"=?,"MediaType"=?,"Size"=?,"Trashed"=?'
        query = 'UPDATE "Items" SET %s WHERE "ItemId"=?' % columns
    elif name == 'insertCapability':
        columns = '"CanAddChild","CanRename","IsReadOnly","IsVersionable","UserId","ItemId"'
        query = 'INSERT INTO "Capabilities" (%s) VALUES (?,?,?,?,?,?)' % columns
    elif name == 'updateCapability':
        columns = '"CanAddChild"=?,"CanRename"=?,"IsReadOnly"=?,"IsVersionable"=?'
        query = 'UPDATE "Capabilities" SET %s WHERE "UserId"=? AND "ItemId"=?' % columns
    elif name == 'deleteParent':
        query = 'DELETE FROM "Parents" WHERE "UserId"=? AND "ChildId"=?'
    elif name == 'insertParent':
        query = 'INSERT INTO "Parents" ("UserId","ChildId","ItemId") VALUES (?,?,?)'
    elif name == 'updateLoaded':
        query = 'UPDATE "Items" SET "Loaded"=? WHERE "ItemId"=?'
    elif name == 'updateTitle':
        query = 'UPDATE "Items" SET "Title"=? WHERE "ItemId"=?'
    elif name == 'updateSize':
        query = 'UPDATE "Items" SET "Size"=? WHERE "ItemId"=?'
    elif name == 'updateTrashed':
        query = 'UPDATE "Items" SET "Trashed"=? WHERE "ItemId"=?'
    elif name == 'insertSyncMode':
        columns = '"SyncId","UserId","ItemId","ParentId","SyncMode"'
        query = 'INSERT INTO "Synchronizes" (%s) VALUES (NULL,?,?,?,?)' % columns
    elif name == 'deleteSyncMode':
        query = 'DELETE FROM "Synchronizes" WHERE "SyncId"=?'
    elif name == 'updateItemId':
        query = 'UPDATE "Items" SET "ItemId"=? WHERE "ItemId"=?'
    elif name == 'insertIdentifier':
        query = 'INSERT INTO "Identifiers"("UserId","Id")VALUES(?,?)'
    return query
