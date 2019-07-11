#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.sdbc import SQLException
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

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
    path = getResourceLocation(ctx, plugin, g_folder)
    url = '%s/%s.odb' % (path, scheme)
    if not getSimpleFile(ctx).exists(url):
        _createDataSource(ctx, scheme, path, url)
    return url

def getDataSourceConnection(ctx, url, logger):
    connection = None
    msg = "Try to connect to DataSource: 1"
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    datasource = dbcontext.getByName(url)
    try:
        connection = datasource.getConnection('', '')
    except Exception as e:
        msg += " ... Error: %s - %s" % (e, traceback.print_exc())
        logger.logp(SEVERE, "DataSource", "getDataSourceConnection()", msg)
    else:
        msg += " ... Done"
        logger.logp(INFO, "DataSource", "getDataSourceConnection()", msg)
    return connection

def getKeyMapFromResult(result, item, provider=None):
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
            continue
        if result.wasNull():
            value = None
        if provider:
            value = provider.transform(name, value)
        item.insertValue(name, value)
    return item

def _createDataSource(ctx, scheme, path, url):
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    datasource = dbcontext.createInstance()
    datasource.URL = _getDataSourceUrl(scheme, path, False)
    path = _getDefaultJarPath(ctx)
    info = (getPropertyValue('JavaDriverClass', g_class),
            getPropertyValue('JavaDriverClassPath', path))
    datasource.Info = info
    datasource.DatabaseDocument.storeAsURL(url, ())
    _createDataBase(datasource, scheme)
    datasource.DatabaseDocument.store()

def _getDataSourceUrl(scheme, url, shutdown):
    path = uno.fileUrlToSystemPath('%s/%s' % (url, scheme))
    return '%sfile:%s%s%s' % (g_protocol, path, g_options, g_shutdow if shutdown else '')

def _getDefaultJarPath(ctx):
    pathsub = ctx.ServiceManager.createInstance('com.sun.star.util.PathSubstitution')
    path = pathsub.substituteVariables('$(prog)', True)
    jarpath = '%s/classes/%s' % (path, g_jar)
    return jarpath

def _createDataBase(datasource, scheme):
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

def _registerDataSource(ctx, path, scheme, location, shutdown=False):
    url = '%s/%s.odb' % (location, scheme)
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if not getSimpleFile(ctx).exists(url):
        _createDataSource(ctx, dbcontext, path, scheme, location, url, shutdown)
    if not dbcontext.hasRegisteredDatabase(scheme):
        dbcontext.registerDatabaseLocation(scheme, url)
    elif dbcontext.getDatabaseLocation(scheme) != url:
        dbcontext.changeDatabaseLocation(scheme, url)
