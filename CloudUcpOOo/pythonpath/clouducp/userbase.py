#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import IllegalIdentifierException

from .unolib import Initialization
from .unolib import PropertySet
from .contenttools import getConnectionMode
from .unotools import getProperty
from .contentcore import getSession
from .dbtools import getItemFromResult
from .dbtools import parseDateTime
from .dbtools import unparseDateTime


class UserBase(object):
    pass


class ContentUserBase(UserBase,
                      unohelper.Base,
                      Initialization,
                      PropertySet):
    def __init__(self, ctx, namedvalues):
        self.ctx = ctx
        self.Scheme = None
        self.Connection = None
        self.Name = None
        self.initialize(namedvalues)
        self._Mode = getConnectionMode(self.ctx, self.getHost())
        self.Error = None
        self.Session = None if self.Name is None else getSession(self.ctx, self.Scheme, self.Name)
        user = self._getUser()
        self.user = {} if user is None else user
        if self.IsValid and self.Mode == ONLINE:
            with self.Session as s:
                self.checkIdentifiers(s)

    @property
    def Id(self):
        return self.user.get('Id', None)
    @property
    def RootId(self):
        return self.user.get('RootId', None)
    @property
    def IsValid(self):
        return all((self.Id, self.Name, self.RootId, self.Error is None))
    @property
    def Mode(self):
        return self._Mode
    @Mode.setter
    def Mode(self, mode):
        if mode == ONLINE and mode != getConnectionMode(self.ctx, self.getHost()):
            return
        self._Mode = mode

    def getHost(self):
        raise NotImplementedError
    def selectUser(self):
        raise NotImplementedError
    def getUser(self, session):
        raise NotImplementedError
    def checkIdentifiers(self, session):
        raise NotImplementedError
    def mergeJsonUser(self, data, root):
        raise NotImplementedError

    def getDateTimeParser(self):
        return parseDateTime
    def unparseDateTime(self, datetime=None):
        return unparseDateTime(datetime)

    def getItemFromResult(self, result, data=None, transform=None):
        return getItemFromResult(result, data, transform)

    def _getUser(self):
        if self.Name is None:
            message = "ERROR: Can't retrieve a UserName from Handler"
            self.Error = IllegalIdentifierException(message, self)
            return None
        user = self.selectUser()
        if user is None:
            if self.Mode == ONLINE:
                user = self._getUserFromProvider()
            else:
                message = "ERROR: Can't retrieve User: %s Network is Offline" % self.Name
                self.Error = IllegalIdentifierException(message, self)
        return user

    def _getUserFromProvider(self):
        user = None
        with self.Session as s:
            data, root = self.getUser(s)
        print("ContentUser._getUserFromProvider(): %s" % self.Name)
        if root is not None:
            user = self.mergeJsonUser(data, root)
        else:
            message = "ERROR: Can't retrieve User: %s from provider" % self.Name
            self.Error = IllegalIdentifierException(message, self)
        return user

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | readonly)
        properties['Mode'] = getProperty('Mode', 'short', bound | readonly)
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['Name'] = getProperty('Name', 'string', maybevoid | bound | readonly)
        properties['RootId'] = getProperty('RootId', 'string', maybevoid | bound | readonly)
        properties['IsValid'] = getProperty('IsValid', 'boolean', bound | readonly)
        properties['Error'] = getProperty('Error', 'com.sun.star.ucb.IllegalIdentifierException', maybevoid | bound | readonly)    
        return properties
