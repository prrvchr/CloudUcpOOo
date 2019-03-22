#!
# -*- coding: utf_8 -*-

import uno

import datetime

from .unotools import getPropertyValue
from .unotools import getResourceLocation
from .unotools import getSimpleFile

RETRIEVED = 0
CREATED = 1
FOLDER = 2
FILE = 4
RENAMED = 8
REWRITED = 16
TRASHED = 32

g_datetime = '%Y-%m-%dT%H:%M:%S.%fZ'

g_protocol = 'jdbc:hsqldb:'
g_folder = 'hsqldb'
g_jar = 'hsqldb.jar'
g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=true'
g_shutdow = ';shutdown=true'


def getDbConnection(ctx, scheme, identifier, shutdown=False):
    location = getResourceLocation(ctx, identifier, g_folder)
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    url = _getUrl(location, scheme, shutdown)
    info = _getInfo(location)
    connection = pool.getConnectionWithInfo(url, info)
    return connection
    
def registerDataBase(ctx, scheme, shutdown=False, url=None):
    location = getResourceLocation(ctx, '') if url is None else url
    url = '%s%s.odb' % (location, scheme)
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if not getSimpleFile(ctx).exists(url):
        _createDataBase(dbcontext, scheme, location, url, shutdown)
    if not dbcontext.hasRegisteredDatabase(scheme):
        dbcontext.registerDatabaseLocation(scheme, url)
    elif dbcontext.getDatabaseLocation(scheme) != url:
        dbcontext.changeDatabaseLocation(scheme, url)
    return url

def _createDataBase(dbcontext, scheme, location, url, shutdown):
    datasource = dbcontext.createInstance()
    datasource.URL = _getUrl(location, scheme, shutdown)
    datasource.Info = _getInfo(location)
    descriptor = (getPropertyValue('Overwrite', True), )
    datasource.DatabaseDocument.storeAsURL(url, descriptor)

def getItemFromResult(result, data=None, transform=None):
    item = {} if data is None else {'Data':{k: None for k in data}}
    for index in range(1, result.MetaData.ColumnCount +1):
        dbtype = result.MetaData.getColumnTypeName(index)
        name = result.MetaData.getColumnName(index)
        if dbtype == 'VARCHAR':
            value = result.getString(index)
        elif dbtype == 'TIMESTAMP':
            value = result.getTimestamp(index)
        elif dbtype == 'BOOLEAN':
            value = result.getBoolean(index)
        elif dbtype == 'BIGINT' or dbtype == 'SMALLINT':
            value = result.getLong(index)
        else:
            continue
        if transform is not None and name in transform:
            print("dbtools.getItemFromResult() 1: %s: %s" % (name, value))
            value = transform[name](value)
            print("dbtools.getItemFromResult() 2: %s: %s" % (name, value))
        if value is None or result.wasNull():
            continue
        if data is not None and name in data:
            item['Data'][name] = value
        else:
            item[name] = value
    return item

def parseDateTime(timestr=None):
    if timestr is None:
        t = datetime.datetime.now()
    else:
        t = datetime.datetime.strptime(timestr, g_datetime)
    return _getDateTime(t.microsecond, t.second, t.minute, t.hour, t.day, t.month, t.year)

def unparseDateTime(t=None):
    if t is None:
        return datetime.datetime.now().strftime(g_datetime)
    millisecond = 0
    if hasattr(t, 'HundredthSeconds'):
        millisecond = t.HundredthSeconds * 10
    elif hasattr(t, 'NanoSeconds'):
        millisecond = t.NanoSeconds // 1000000
    return '%s-%s-%sT%s:%s:%s.%03dZ' % (t.Year, t.Month, t.Day, t.Hours, t.Minutes, t.Seconds, millisecond)

def _getDateTime(microsecond=0, second=0, minute=0, hour=0, day=1, month=1, year=1970, utc=True):
    t = uno.createUnoStruct('com.sun.star.util.DateTime')
    t.Year = year
    t.Month = month
    t.Day = day
    t.Hours = hour
    t.Minutes = minute
    t.Seconds = second
    if hasattr(t, 'HundredthSeconds'):
        t.HundredthSeconds = microsecond // 10000
    elif hasattr(t, 'NanoSeconds'):
        t.NanoSeconds = microsecond * 1000
    if hasattr(t, 'IsUTC'):
        t.IsUTC = utc
    return t


def _getUrl(location, scheme, shutdown):
    return '%s%s/%s%s%s' % (g_protocol, location, scheme, g_options, g_shutdow if shutdown else '')

def _getInfo(location):
    path = '%s/%s' % (location, g_jar)
    return (getPropertyValue('JavaDriverClass', g_class), 
            getPropertyValue('JavaDriverClassPath', path))
