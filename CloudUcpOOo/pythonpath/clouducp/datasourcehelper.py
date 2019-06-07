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


def _registerJavaClass(ctx, location):
    try:
        print("DataSourceHelper._registerJavaClass() 1: %s" % location)
        path = _getDataSourceClassPath(location)
        configuration = getConfiguration(ctx, 'org.openoffice.Office.Java')
        print("DataSourceHelper._registerJavaClass() 2: %s" % path)
        vm = configuration.getByName('VirtualMachine')
        if vm.UserClassPath != path:
            #classpath = vm.getByName('UserClassPath')
            print("DataSourceHelper._registerJavaClass() 3: '%s'" % vm.UserClassPath)
            #if not classpath:
            #mri = ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(configuration)
            #vm.UserClassPath = path
            print("DataSourceHelper._registerJavaClass() 4: %s" % vm.getByName('UserClassPath'))
            if configuration.hasPendingChanges():
                print("DataSourceHelper._registerJavaClass() 5")
            configuration.commitChanges()
            print("DataSourceHelper._registerJavaClass() 6")
    except Exception as e:
        print("DataSourceHelper._registerJavaClass().Error: %s - %s" % (e, traceback.print_exc()))

def getDataSourceUrl(ctx, scheme, plugin):
    error = ''
    url = getResourceLocation(ctx, plugin, '%s.odb' % scheme)
    print("DataSourceHelper.getDataSourceUrl() 1: %s" % url)
    if not getSimpleFile(ctx).exists(url):
        error = "Error: can't open DataSource file: %s doesn't exist" % url
    print("DataSourceHelper.getDataSourceUrl() 2: %s" % error)
    return error, url

def getDataSourceConnection(ctx, scheme, url):
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

def _createDataSource(ctx, dbcontext, path, scheme, location, url, shutdown):
    print("DataSourceHelper._createDataSource() 1")
    datasource = dbcontext.createInstance()
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

def _getDataSourceUrl(scheme, location, shutdown):
    return '%s%s/%s%s%s' % (g_protocol, location, scheme, g_options, g_shutdow if shutdown else '')

def _getDataSourcePath(scheme, location, shutdown):
    path = uno.fileUrlToSystemPath(location)
    print("DataSourceHelper._getDataSourcePath() 1: %s" % path)
    return '%sfile:%s/%s%s%s' % (g_protocol, path, scheme, g_options, g_shutdow if shutdown else '')

def _getDataSourceClassPath(location):
    path = location
    print("DataSourceHelper._getDataSourceClassPath() 1: %s" % path)
    return '%s/%s' % (path, g_jar)

def setUserData(provider, call, user, root):
    call.setString(1, provider.getUserId(user))
    call.setString(2, provider.getUserName(user))
    call.setString(3, provider.getUserDisplayName(user))
    call.setString(4, provider.getRootId(root))

def setRootData(provider, call, root, timestamp, i=1):
    call.setString(i, provider.getRootId(root))
    i += 1
    call.setString(i, provider.getRootName(root))
    i += 1
    call.setString(i, provider.getRootCreated(root, timestamp))
    i += 1
    call.setString(i, provider.getRootModified(root, timestamp))
    i += 1
    call.setString(i, provider.getRootMediaType(root))
    i += 1
    call.setLong(i, provider.getRootSize(root))
    i += 1
    call.setBoolean(i, provider.getRootTrashed(root))
    i += 1
    call.setBoolean(i, provider.getRootCanAddChild(root))
    i += 1
    call.setBoolean(i, provider.getRootCanRename(root))
    i += 1
    call.setBoolean(i, provider.getRootIsReadOnly(root))
    i += 1
    call.setBoolean(i, provider.getRootIsVersionable(root))
    i += 1
    return i

def setItemData(provider, call, item, timestamp, i=1):
    call.setString(i, provider.getItemId(item))
    i += 1
    call.setString(i, provider.getItemName(item))
    i += 1
    call.setString(i, provider.getItemCreated(item, timestamp))
    i += 1
    call.setString(i, provider.getItemModified(item, timestamp))
    i += 1
    call.setString(i, provider.getItemMediaType(item))
    i += 1
    call.setLong(i, provider.getItemSize(item))
    i += 1
    call.setBoolean(i, provider.getItemTrashed(item))
    i += 1
    call.setBoolean(i, provider.getItemCanAddChild(item))
    i += 1
    call.setBoolean(i, provider.getItemCanRename(item))
    i += 1
    call.setBoolean(i, provider.getItemIsReadOnly(item))
    i += 1
    call.setBoolean(i, provider.getItemIsVersionable(item))
    i += 1
    return i

def setItemParent(provider, call, item, rootid, i=1):
    call.setString(i, provider.getItemParent(item, rootid))
    i += 1
    return i

def setContentData(call, data, i=1):
    call.setString(i, data.getValue('Title'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('Title')))
    i += 1
    call.setTimestamp(i, data.getValue('DateCreated'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('DateCreated')))
    i += 1
    call.setTimestamp(i, data.getValue('DateModified'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('DateModified')))
    i += 1
    call.setString(i, data.getValue('MediaType'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('MediaType')))
    i += 1
    call.setLong(i, data.getValue('Size'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('Size')))
    i += 1
    call.setBoolean(i, data.getValue('Trashed'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('Trashed')))
    i += 1
    call.setBoolean(i, data.getValue('CanAddChild'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('CanAddChild')))
    i += 1
    call.setBoolean(i, data.getValue('CanRename'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('CanRename')))
    i += 1
    call.setBoolean(i, data.getValue('IsReadOnly'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('IsReadOnly')))
    i += 1
    call.setBoolean(i, data.getValue('IsVersionable'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('IsVersionable')))
    i += 1
    call.setBoolean(i, data.getValue('Loaded'))
    print("DataSource.insertContent() %s %s" % (i, data.getValue('Loaded')))
    i += 1
    return i

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
