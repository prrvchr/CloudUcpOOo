#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.sdb import ParametersRequest
from com.sun.star.connection import NoConnectException
from com.sun.star.ucb import InteractiveAugmentedIOException
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.ConnectionMode import OFFLINE

from .configuration import g_identifier

from .unotools import getProperty
from .unotools import getPropertyValue
from .unotools import getNamedValueSet


def getConnectionMode(ctx, host):
    return getSessionMode(ctx, host)

def getSessionMode(ctx, host):
    connector = ctx.ServiceManager.createInstance('com.sun.star.connection.Connector')
    try:
        connection = connector.connect('socket,host=%s,port=80' % host)
    except NoConnectException:
        mode = OFFLINE
    else:
        connection.close()
        mode = ONLINE
    return mode

def createContentUser(ctx, datasource, plugin, username=None):
    service = '%s.ContentUser' % plugin
    namedvalue = getNamedValueSet({'DataSource': datasource, 'Name': username})
    contentuser = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return contentuser

def createContentIdentifier(ctx, plugin, user, uri):
    service = '%s.ContentIdentifier' % plugin
    namedvalue = getNamedValueSet({'User': user, 'Uri': uri})
    contentidentifier = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return contentidentifier

def createContent(ctx, identifier, data, plugin, folder, link, documents):
    content, service = None, None
    mimetype = data.get('MimeType', 'application/octet-stream')
    if mimetype == folder:
        service = '%s.FolderContent' % g_identifier
    elif mimetype == link:
        pass
    elif mimetype in (documents):
        service = '%s.DocumentContent' % plugin
    else:
        service = '%s.DocumentContent' % g_identifier
    if service is not None:
        namedvalue = getNamedValueSet({'Identifier': identifier})
        namedvalue += getNamedValueSet(data)
        content = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return content

def propertyChange(source, name, oldvalue, newvalue):
    if name in source.propertiesListener:
        events = (_getPropertyChangeEvent(source, name, oldvalue, newvalue), )
        for listener in source.propertiesListener[name]:
            listener.propertiesChange(events)

def setContentData(content, call, properties, index=1):
    row = _getContentProperties(content, properties)
    for i, name in enumerate(properties, 1):
        value = row.getObject(i, None)
        print ("items._setContentData(): name:%s - value:%s" % (name, value))
        if value is None:
            continue
        if name in ('Name', 'MimeType'):
            call.setString(index, value)
        elif name in ('DateCreated', 'DateModified'):
            call.setTimestamp(index, value)
        elif name in ('Trashed', 'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable'):
            call.setBoolean(index, value)
        elif name in ('Size', 'Loaded'):
            call.setLong(index, value)
        index += 1
    return index

def _getContentProperties(content, properties):
    namedvalues = []
    for name in properties:
        namedvalues.append(getProperty(name))
    command = getCommand('getPropertyValues', tuple(namedvalues))
    return content.execute(command, 0, None)

def _getPropertyChangeEvent(source, name, oldvalue, newvalue, further=False, handle=-1):
    event = uno.createUnoStruct('com.sun.star.beans.PropertyChangeEvent')
    event.Source = source
    event.PropertyName = name
    event.Further = further
    event.PropertyHandle = handle
    event.OldValue = oldvalue
    event.NewValue = newvalue
    return event

def getPump(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pump')

def getPipe(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pipe')

def getContentEvent(source, action, content, id):
    event = uno.createUnoStruct('com.sun.star.ucb.ContentEvent')
    event.Source = source
    event.Action = action
    event.Content = content
    event.Id = id
    return event

def getCommand(name, argument, handle=-1):
    command = uno.createUnoStruct('com.sun.star.ucb.Command')
    command.Name = name
    command.Handle = handle
    command.Argument = argument
    return command

def getCommandInfo(name, typename=None, handle=-1):
    command = uno.createUnoStruct('com.sun.star.ucb.CommandInfo')
    command.Name = name
    command.Handle = handle
    if typename is not None:
        command.ArgType = uno.getTypeByName(typename)
    return command

def getContentInfo(ctype, attributes=0, properties=()):
    info = uno.createUnoStruct('com.sun.star.ucb.ContentInfo')
    info.Type = ctype
    info.Attributes = attributes
    info.Properties = properties
    return info

def getUri(ctx, identifier):
    factory = ctx.ServiceManager.createInstance('com.sun.star.uri.UriReferenceFactory')
    uri = factory.parse(identifier)
    return uri

def getUcb(ctx, arguments=('Local', 'Office')):
    name = 'com.sun.star.ucb.UniversalContentBroker'
    return ctx.ServiceManager.createInstanceWithArguments(name, (arguments, ))

def getUcp(ctx, scheme):
    return getUcb(ctx).queryContentProvider('%s://' % scheme)

def getMimeType(ctx, stream):
    mimetype = 'application/octet-stream'
    detection = ctx.ServiceManager.createInstance('com.sun.star.document.TypeDetection')
    descriptor = (getPropertyValue('InputStream', stream), )
    format, dummy = detection.queryTypeByDescriptor(descriptor, True)
    if detection.hasByName(format):
        properties = detection.getByName(format)
        for property in properties:
            if property.Name == "MediaType":
                mimetype = property.Value
    return mimetype

def getParametersRequest(source, connection, message):
    r = ParametersRequest()
    r.Message = message
    r.Context = source
    r.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
    r.Connection = connection
    return r

def getInteractiveAugmentedIOException(message, source, Classification, code, arguments):
    e = InteractiveAugmentedIOException()
    e.Message = message
    e.Context = source
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', Classification)
    e.Code = uno.Enum('com.sun.star.ucb.IOErrorCode', code)
    e.Arguments = arguments
    return e
