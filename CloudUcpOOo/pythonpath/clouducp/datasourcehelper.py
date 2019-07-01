#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.sdbc import SQLException

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
from .datasourcequeries import getSqlQuery

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

def getKeyMapFromResult(result, keymap=None, provider=None):
    item = KeyMap() if keymap is None else keymap
    #print("DataSource._getKetMapFromResult() %s" % result.MetaData.ColumnCount)
    for i in range(1, result.MetaData.ColumnCount +1):
        name = result.MetaData.getColumnName(i)
        dbtype = result.MetaData.getColumnTypeName(i)
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

def _getDataSourceUrl(scheme, url, shutdown):
    location = uno.fileUrlToSystemPath(url)
    return '%sfile:%s/%s%s%s' % (g_protocol, location, scheme, g_options, g_shutdow if shutdown else '')

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
