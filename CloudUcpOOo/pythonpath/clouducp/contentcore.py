#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException
from com.sun.star.lang import IllegalArgumentException, IllegalAccessException
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ContentAction import INSERTED
from com.sun.star.ucb.ContentAction import REMOVED
from com.sun.star.ucb.ContentAction import DELETED
from com.sun.star.ucb.ContentAction import EXCHANGED
from com.sun.star.uno import Exception as UnoException

from .children import countChildTitle
from .contenttools import getCommand
from .contenttools import getContentEvent
from .contenttools import getUcp
from .contenttools import getInteractiveAugmentedIOException
from .items import insertContentItem
from .items import updateLoaded
from .items import updateName
from .items import updateSize
from .items import updateTrashed
from .unotools import getInteractionHandler
from .unotools import getNamedValue
from .unotools import getPropertyValueSet


def getPropertiesValues(source, properties, logger):
    namedvalues = []
    for property in properties:
        value = None
        msg = "ERROR: Requested property: %s as incorect type" % property
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        if hasattr(property, 'Name') and hasattr(source, property.Name):
            value = getattr(source, property.Name)
            msg = "Get property: %s value: %s" % (property.Name, value)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        else:
            msg = "ERROR: Requested property: %s is not available" % property.Name
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        logger.logp(level, source.__class__.__name__, "getPropertiesValues()", msg)
        print("%s.getPropertiesValues() %s" % (source.__class__.__name__, msg))
        namedvalues.append(getNamedValue(property.Name, value))
    return tuple(namedvalues)

def setPropertiesValues(source, context, properties, propertyset, logger):
    results = []
    readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
    for position, property in enumerate(properties):
        if hasattr(property, 'Name') and hasattr(property, 'Value'):
            name, value = property.Name, property.Value
            result, level, msg = _setPropertyValue(source, context, propertyset, name, value, position, readonly)
        else:
            msg = "ERROR: Requested property: %s as incorect type" % property
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            error = UnoException(msg, source)
            result = uno.Any('com.sun.star.uno.Exception', error)
        logger.logp(level, source.__class__.__name__, "setPropertiesValues()", msg)
        print("%s.setPropertiesValues() %s" % (source.__class__.__name__, msg))
        results.append(result)
    return tuple(results)

def _setPropertyValue(source, context, propertyset, name, value, position, readonly):
    if name in propertyset:
        if propertyset.get(name).Attributes & readonly:
            msg = "ERROR: Requested property: %s is READONLY" % name
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            error = IllegalAccessException(msg, source)
            result = uno.Any('com.sun.star.lang.IllegalAccessException', error)
        else:
            result, level, msg = _setProperty(source, context, name, value, position)
    else:
        msg = "ERROR: Requested property: %s is not available" % name
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        error = UnknownPropertyException(msg, source)
        result = uno.Any('com.sun.star.beans.UnknownPropertyException', error)
    return result, level, msg

def _setProperty(source, context, name, value, position):
    if name == 'Title':
        result, level, msg = _setTitle(source, context, value, position)
    else:
        setattr(source, name, value)
        msg = "Set property: %s value: %s" % (name, value)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        result = None
    return result, level, msg

def _setTitle(source, context, title, position):
    identifier = source.getIdentifier()
    if u'~' in title:
        msg = "Can't set property: %s value: %s contains invalid character: '~'." % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        data = getPropertyValueSet({'Uri': identifier.getContentIdentifier(),'ResourceName': title})
        error = getInteractiveAugmentedIOException(msg, context, 'ERROR', 'INVALID_CHARACTER', data)
        result = uno.Any('com.sun.star.ucb.InteractiveAugmentedIOException', error)
    elif countChildTitle(identifier.getParent(), title):
        msg = "Can't set property: %s value: %s - Name Clash Error" % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        data = getPropertyValueSet({'Uri': identifier.getContentIdentifier(),'ResourceName': title})
        error = getInteractiveAugmentedIOException(msg, context, 'ERROR', 'ALREADY_EXISTING', data)
        result = uno.Any('com.sun.star.ucb.InteractiveAugmentedIOException', error)
    else:
        setattr(source, 'Title', title)
        msg = "Set property: %s value: %s" % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        result = None
    return result, level, msg

def updateContent(ctx, event):
    print("contentcore.updateContent() %s - %s" % (event.PropertyName, event.NewValue))
    name, update, result = event.PropertyName, True, False
    identifier = event.Source.getIdentifier()
    if name == 'Id':
        result = insertContentItem(event.Source, identifier, event.NewValue)
    elif name == 'Trashed':
        result = updateTrashed(identifier, event.NewValue)
        #if result:
        #    event.Source.notify(getContentEvent(event.Source, DELETED, event.Source, identifier))
        #action = DELETED
    if name  == 'Name':
        result = updateName(identifier, event.NewValue)
    elif name == 'Size':
        result = updateSize(identifier, event.NewValue)
    elif name == 'Loaded':
        result = updateLoaded(identifier, event.NewValue)
        update = False
    if update and result:
        identifier.update()
        result = identifier.Updated
    print("contentcore.updateContent() %s" % result)
    return result

def notifyContentListener(ctx, source, action, identifier=None):
    if action == INSERTED:
        identifier = source.getIdentifier().getParent()
        parent = getUcp(ctx, identifier.getContentProviderScheme()).queryContent(identifier)
        parent.notify(getContentEvent(action, source, identifier))
    elif action == DELETED:
        identifier = source.getIdentifier()
        source.notify(getContentEvent(action, source, identifier))
    elif action == EXCHANGED:
        source.notify(getContentEvent(action, source, identifier))

def executeContentCommand(content, name, argument, environment):
    command = getCommand(name, argument)
    return content.execute(command, 0, environment)
