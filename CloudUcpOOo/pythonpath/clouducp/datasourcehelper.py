#!
# -*- coding: utf_8 -*-

import unohelper

from com.sun.star.sdbc import SQLException

from .keymap import KeyMap
from .unotools import getPropertyValue
from .unotools import getResourceLocation
from .configuration import g_identifier
from .configuration import g_protocol
from .configuration import g_folder
from .configuration import g_jar
from .configuration import g_class
from .configuration import g_options
from .configuration import g_shutdow


def getDataSourceUrl(ctx, scheme, plugin, shutdown=False):
    # ToDo check if 'hsqldb.jar' is in Libre/OpenOffice 'ClassPath' and add it if not...
    location = getResourceLocation(ctx, plugin, g_folder)
    return '%s%s/%s%s%s' % (g_protocol, location, scheme, g_options, g_shutdow if shutdown else '')

def getDataSourceConnection(ctx, url):
    connection = None
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    info = _getInfo(ctx)
    try:
        connection = pool.getConnectionWithInfo(url, info)
    except SQLException:
        pass
    return connection

def setUserData(provider, call, user, i=1):
    call.setString(i, provider.getUserId(user))
    i += 1
    call.setString(i, provider.getUserName(user))
    i += 1
    call.setString(i, provider.getUserDisplayName(user))
    i += 1
    return i

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

def getKetMapFromResult(result, keymap=None, provider=None):
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

def _getInfo(ctx):
    location = getResourceLocation(ctx, g_identifier, g_folder)
    path = '%s/%s' % (location, g_jar)
    return (getPropertyValue('JavaDriverClass', g_class),
            getPropertyValue('JavaDriverClassPath', path))
