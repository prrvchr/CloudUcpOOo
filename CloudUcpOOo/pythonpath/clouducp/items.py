#!
# -*- coding: utf_8 -*-

import uno

from .contenttools import setContentData
from .dbtools import RETRIEVED
from .dbtools import RENAMED
from .dbtools import REWRITED
from .dbtools import TRASHED


def insertContentItem(content, identifier, value):
    properties = identifier.Properties
    call = 'CALL "insertContentItem"(%s)' % ','.join(['?'] * (len(properties) +5))
    print("items.insertContentItem() %s - %s - %s" % (identifier.getContentIdentifier(), properties, call))
    insert = identifier.User.Connection.prepareCall(call)
    insert.setString(1, identifier.User.Id)
    insert.setString(2, identifier.Id)
    insert.setString(3, identifier.getParent().Id)
    insert.setString(4, value)
    index = setContentData(content, insert, properties, 5)
    insert.execute()
    result = insert.getLong(index)
    insert.close()
    return result

def updateName(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateName"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setString(3, value)
    update.setLong(4, RENAMED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateSize(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateSize"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.setLong(4, REWRITED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateTrashed(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateTrashed"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.setLong(4, TRASHED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateLoaded(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateLoaded"(?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.execute()
    result = update.getLong(4)
    update.close()
    return result
