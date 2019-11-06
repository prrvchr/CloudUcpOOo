#!
# -*- coding: utf_8 -*-


from .unotools import getResourceLocation
from .unotools import getSimpleFile

from .dbtools import getCreateTableQueries
from .dbtools import registerDataSource
from .dbtools import executeQueries
from .dbtools import getDataSourceLocation
from .dbtools import getDataSourceInfo
from .dbtools import getDataSourceJavaInfo

from .dbqueries import getSqlQuery
from .configuration import g_path

import traceback


def getDataSourceUrl(ctx, dbctx, dbname, plugin, register):
    location = getResourceLocation(ctx, plugin, g_path)
    url = '%s/%s.odb' % (location, dbname)
    if not getSimpleFile(ctx).exists(url):
        _createDataSource(ctx, dbctx, url, location, dbname)
        if register:
            registerDataSource(dbctx, dbname, url)
    return url

def _createDataSource(ctx, dbcontext, url, location, dbname):
    datasource = dbcontext.createInstance()
    datasource.URL = getDataSourceLocation(location, dbname, False)
    datasource.Info = getDataSourceInfo() + getDataSourceJavaInfo(location)
    datasource.DatabaseDocument.storeAsURL(url, ())
    _createDataBase(datasource)
    datasource.DatabaseDocument.store()

def _createDataBase(datasource):
    connection = datasource.getConnection('', '')
    statement = connection.createStatement()
    tables, views = _getTablesAndViews()
    _createStaticTable(statement, tables)
    executeQueries(statement, views)
    _createDynamicTable(statement)
    executeQueries(statement, _getViews())
    connection.close()
    connection.dispose()

def _createStaticTable(statement, tables):
    for table in tables:
        query = getSqlQuery('createTable' + table)
        print("dbtool._createStaticTable(): %s" % query)
        statement.executeQuery(query)
    for table in tables:
        statement.executeQuery(getSqlQuery('setTableSource', table))
        statement.executeQuery(getSqlQuery('setTableReadOnly', table))

def _createDynamicTable(statement):
    queries = getCreateTableQueries(statement)
    _executeQueries(statement, queries)

def _executeQueries(statement, queries):
    for query in queries:
        statement.executeQuery(query)

def _getTablesAndViews():
    tables = ('Tables',
              'Columns',
              'TableColumn',
              'Settings')
    views = ('createTableView', )
    return tables, views

def _getViews():
    return ('createItemView',
            'createChildView',
            'createSyncView')
