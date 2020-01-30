#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.sdbc import SQLException
from com.sun.star.sdbc import SQLWarning

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from unolib import KeyMap
from unolib import getPropertyValue
from unolib import getPropertyValueSet
from unolib import getResourceLocation
from unolib import getSimpleFile

from .dbqueries import getSqlQuery

from .dbconfig import g_protocol
from .dbconfig import g_path
from .dbconfig import g_jar
from .dbconfig import g_class
from .dbconfig import g_options
from .dbconfig import g_shutdown
from .dbconfig import g_version

import traceback


def getDataSourceConnection(ctx, url, dbname, name='', password=''):
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    odb = '%s/%s.odb' % (url, dbname)
    print("dbtools.getDataSourceConnection() 1")
    datasource = dbcontext.getByName(odb)
    connection, error = None, None
    try:
        connection = datasource.getConnection(name, password)
    except SQLException as e:
        error = e
    print("dbtools.getDataSourceConnection() 2")
    return connection, error

def getDataBaseConnection(ctx, url, dbname, name='', password='', shutdown=False):
    info = getDataSourceJavaInfo(url)
    if name != '':
        info += getPropertyValueSet({'user': name})
        if password != '':
            info += getPropertyValueSet({'password': password})
    path = getDataSourceLocation(url, dbname, shutdown)
    manager = ctx.ServiceManager.createInstance('com.sun.star.sdbc.DriverManager')
    connection, error = None, None
    try:
        connection = manager.getConnectionWithInfo(path, info)
    except SQLException as e:
        error = e
    print("dbtools.getDataBaseConnection()")
    return connection, error

def getDataSourceCall(connection, name, format=None):
    query = getSqlQuery(name, format)
    call = connection.prepareCall(query)
    return call

def createDataSource(dbcontext, location, dbname, shutdown=False):
    datasource = dbcontext.createInstance()
    datasource.URL = getDataSourceLocation(location, dbname, shutdown)
    datasource.Info = getDataSourceInfo() + getDataSourceJavaInfo(location)
    return datasource

def checkDataBase(connection):
    error = None
    version = connection.getMetaData().getDriverVersion()
    if version != g_version:
        error = SQLException()
        error.Message = "DataBase ERROR: hsqldb driver %s is not the correct version... " % g_jar
        error.Message += "Requiered version: %s - loaded version: %s" % (g_version, version)
    return version, error

def executeQueries(statement, queries):
    for query in queries:
        statement.executeQuery(getSqlQuery(query))

def getDataSourceJavaInfo(location):
    info = {}
    info['JavaDriverClass'] = g_class
    info['JavaDriverClassPath'] = '%s/%s' % (location, g_jar)
    return getPropertyValueSet(info)

def getDataSourceInfo():
    info = getDataBaseInfo()
    return getPropertyValueSet(info)

def getDataBaseInfo():
    info = {}
    info['AppendTableAliasName'] = True
    info['AutoIncrementCreation'] = 'GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY'
    info['AutoRetrievingStatement'] = 'CALL IDENTITY()'
    info['DisplayVersionColumns'] = True
    info['GeneratedValues'] = True
    info['IsAutoRetrievingEnabled'] = True
    info['ParameterNameSubstitution'] = True
    info['UseIndexDirectionKeyword'] = True
    return info

def getDriverInfo():
    info = {}
    info['AddIndexAppendix'] = True
    info['BaseDN'] = ''
    info['BooleanComparisonMode'] = 0
    info['CharSet'] = ''
    info['ColumnAliasInOrderBy'] = True
    info['CommandDefinitions'] = ''
    info['DecimalDelimiter'] = '.'

    info['EnableOuterJoinEscape'] = True
    info['EnableSQL92Check'] = False
    info['EscapeDateTime'] = True
    info['Extension'] = ''
    info['FieldDelimiter'] = ','
    info['Forms'] = ''
    info['FormsCheckRequiredFields'] = True
    info['GenerateASBeforeCorrelationName'] = False

    info['HeaderLine'] = True
    info['HostName'] = ''
    info['IgnoreCurrency'] = False
    info['IgnoreDriverPrivileges'] = True
    info['IndexAlterationServiceName'] = ''
    info['KeyAlterationServiceName'] = ''
    info['LocalSocket'] = ''

    info['MaxRowCount'] = 100
    info['Modified'] = True
    info['NamedPipe'] = ''
    info['NoNameLengthLimit'] = False
    info['PortNumber'] = 389
    info['PreferDosLikeLineEnds'] = False
    info['Reports'] = ''

    info['RespectDriverResultSetType'] = False
    info['ShowColumnDescription'] = False
    info['ShowDeleted'] = False
    info['StringDelimiter'] = '"'
    info['SystemDriverSettings'] = ''
    info['TableAlterationServiceName'] = ''
    info['TableRenameServiceName'] = ''
    info['TableTypeFilterMode'] = 3

    info['ThousandDelimiter'] = ''
    info['UseCatalog'] = False
    info['UseCatalogInSelect'] = True
    info['UseSchemaInSelect'] = True
    info['ViewAccessServiceName'] = ''
    info['ViewAlterationServiceName'] = ''
    return info

def getDataSourceLocation(location, dbname, shutdown=False):
    url = uno.fileUrlToSystemPath('%s/%s' % (location, dbname))
    return '%sfile:%s%s%s' % (g_protocol, url, g_options, g_shutdown if shutdown else '')

def registerDataSource(dbcontext, dbname, url):
    if not dbcontext.hasRegisteredDatabase(dbname):
        dbcontext.registerDatabaseLocation(dbname, url)
    elif dbcontext.getDatabaseLocation(dbname) != url:
        dbcontext.changeDatabaseLocation(dbname, url)

def getKeyMapFromResult(result, keymap=KeyMap(), provider=None):
    for i in range(1, result.MetaData.ColumnCount +1):
        name = result.MetaData.getColumnName(i)
        dbtype = result.MetaData.getColumnTypeName(i)
        value = _getValueFromResult(result, dbtype, i)
        if value is None:
            continue
        if result.wasNull():
            value = None
        if provider:
            value = provider.transform(name, value)
        keymap.insertValue(name, value)
    return keymap

def getDataFromResult(result, provider=None):
    data = {}
    for i in range(1, result.MetaData.ColumnCount +1):
        name = result.MetaData.getColumnName(i)
        dbtype = result.MetaData.getColumnTypeName(i)
        value = _getValueFromResult(result, dbtype, i)
        if value is None:
            continue
        if result.wasNull():
            value = None
        if provider:
            value = provider.transform(name, value)
        data[name] = value
    return data

def getKeyMapSequenceFromResult(result, provider=None):
    sequence = []
    count = result.MetaData.ColumnCount +1
    while result.next():
        keymap = KeyMap()
        for i in range(1, count):
            name = result.MetaData.getColumnName(i)
            dbtype = result.MetaData.getColumnTypeName(i)
            value = _getValueFromResult(result, dbtype, i)
            if value is None:
                continue
            if result.wasNull():
                value = None
            if provider:
                value = provider.transform(name, value)
            keymap.insertValue(name, value)
        sequence.append(keymap)
    return sequence

def getSequenceFromResult(result, sequence=None, index=1, provider=None):
    # TODO: getSequenceFromResult(result, sequence=[], index=1, provider=None) is buggy
    # TODO: sequence has the content of last method call!!! sequence must be initialized...
    if sequence is None:
        sequence = []
    i = result.MetaData.ColumnCount
    if 0 < index < i:
        i = index
    if not i:
        return sequence
    name = result.MetaData.getColumnName(i)
    dbtype = result.MetaData.getColumnTypeName(i)
    while result.next():
        value = _getValueFromResult(result, dbtype, i)
        if value is None:
            continue
        if result.wasNull():
            value = None
        if provider:
            value = provider.transform(name, value)
        sequence.append(value)
    return sequence

def _getValueFromResult(result, dbtype, index):
    if dbtype == 'VARCHAR':
        value = result.getString(index)
    elif dbtype == 'TIMESTAMP':
        value = result.getTimestamp(index)
    elif dbtype == 'BOOLEAN':
        value = result.getBoolean(index)
    elif dbtype == 'BIGINT' or dbtype == 'SMALLINT' or dbtype == 'INTEGER':
        value = result.getLong(index)
    else:
        value = None
    return value

def getTablesAndStatements(statement, version=g_version):
    tables = []
    statements = {}
    call = getDataSourceCall(statement.getConnection(), 'getTables')
    for table in getSequenceFromResult(statement.executeQuery(getSqlQuery('getTableName'))):
        statement = False
        versioned = False
        columns = []
        primary = []
        unique = []
        constraint = []
        call.setString(1, table)
        result = call.executeQuery()
        while result.next():
            data = getKeyMapFromResult(result, KeyMap())
            statement = data.getValue('View')
            versioned = data.getValue('Versioned')
            column = data.getValue('Column')
            definition = '"%s"' % column
            definition += ' %s' % data.getValue('Type')
            lenght = data.getValue('Lenght')
            definition += '(%s)' % lenght if lenght else ''
            default = data.getValue('Default')
            definition += ' DEFAULT %s' % default if default else ''
            options = data.getValue('Options')
            definition += ' %s' % options if options else ''
            columns.append(definition)
            if data.getValue('Primary'):
                primary.append('"%s"' % column)
            if data.getValue('Unique'):
                unique.append({'Table': table, 'Column': column})
            if data.getValue('ForeignTable') and data.getValue('ForeignColumn'):
                constraint.append({'Table': table,
                                   'Column': column,
                                   'ForeignTable': data.getValue('ForeignTable'),
                                   'ForeignColumn': data.getValue('ForeignColumn')})
        if primary:
            columns.append(getSqlQuery('getPrimayKey', primary))
        for format in unique:
            columns.append(getSqlQuery('getUniqueConstraint', format))
        for format in constraint:
            columns.append(getSqlQuery('getForeignConstraint', format))
        if version >= '2.5.0' and versioned:
            columns.append(getSqlQuery('getPeriodColumns'))
        format = (table, ','.join(columns))
        query = getSqlQuery('createTable', format)
        if version >= '2.5.0' and versioned:
            query += getSqlQuery('getSystemVersioning')
        print("dbtool._createDynamicTable(): %s" % query)
        tables.append(query)
        if statement:
            names = ['"Value"']
            values = ['?']
            where = []
            for format in constraint:
                names.append('"%s"' % format['Column'])
                values.append('?')
                where.append('"%s"=?' % format['Column'])
            insert = 'INSERT INTO "%s" (%s) VALUES (%s)' % (table, ','.join(names), ','.join(values))
            update = 'UPDATE "%s" SET "Value"=?,"TimeStamp"=? WHERE %s' % (table, ' AND '.join(where))
            print("dbtools.getCreateTableQueries() Insert: %s" % insert)
            print("dbtools.getCreateTableQueries() Update: %s" % update)
            statements['insert%s' % table] = insert
            statements['update%s' % table] = update
    call.close()
    return tables, statements

def createStaticTable(statement, tables, readonly=False):
    for table in tables:
        query = getSqlQuery('createTable' + table)
        print("dbtools.createStaticTable(): %s" % query)
        statement.executeQuery(query)
    for table in tables:
        statement.executeQuery(getSqlQuery('setTableSource', table))
        if readonly:
            statement.executeQuery(getSqlQuery('setTableReadOnly', table))

def executeSqlQueries(statement, queries):
    for query in queries:
        print("dbtools.executeSqlQueries(): %s" % query)
        statement.executeQuery(query)

def getWarning(state, code, message, context=None, exception=None):
    warning = SQLWarning()
    warning.SQLState = state
    warning.ErrorCode = code
    warning.NextException = exception
    warning.Message = message
    warning.Context = context
    return warning
