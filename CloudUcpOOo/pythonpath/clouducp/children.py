#!
# -*- coding: utf_8 -*-

import uno


def countChildTitle(identifier, title):
    count = 1
    call = identifier.User.Connection.prepareCall('CALL "countChildTitle"(?, ?, ?)')
    call.setString(1, identifier.User.Id)
    call.setString(2, identifier.Id)
    call.setString(3, title)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def isChildId(identifier, id):
    ischild = False
    call = identifier.User.Connection.prepareCall('CALL "isChildId"(?, ?)')
    call.setString(1, identifier.Id)
    call.setString(2, id)
    result = call.executeQuery()
    if result.next():
        ischild = result.getBoolean(1)
    call.close()
    return ischild

def selectChildId(connection, parent, uri):
    id = None
    call = connection.prepareCall('CALL "selectChildId"(?, ?)')
    call.setString(1, parent)
    call.setString(2, uri)
    result = call.executeQuery()
    if result.next():
        id = result.getString(1)
    call.close()
    return id

def getChildSelect(identifier):
    print("children.getChildSelect() 1")
    # LibreOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    # OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    index, select = 1, identifier.User.Connection.prepareCall('CALL "selectChild"(?, ?, ?, ?, ?)')
    print("children.getChildSelect() 2")
    # select return RowCount as OUT parameter in select.getLong(index)!!!
    # Never managed to run the next line:
    # select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
    # selectChild(IN ID VARCHAR(100),IN URL VARCHAR(250),IN MODE SMALLINT,OUT ROWCOUNT SMALLINT)
    select.setString(index, identifier.User.Id)
    index += 1
    select.setString(index, identifier.Id)
    index += 1
    # "TargetURL" is done by CONCAT(BaseURL,'/',Title or Id)...
    select.setString(index, identifier.BaseURL)
    index += 1
    select.setLong(index, identifier.User.Mode)
    index += 1
    print("children.getChildSelect() 3")
    return index, select
