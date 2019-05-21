#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb import XRestRequest

from .requesthelper import Enumerator
from .requesthelper import InputStream
from .requesthelper import OutputStream
from .requesthelper import getSessionMode
from .requesthelper import getSession
from .requesthelper import execute
from .configuration import g_timeout


class Request(unohelper.Base,
              XRestRequest):
    def __init__(self, ctx):
        self.ctx = ctx
        self.Session = None
        self.Error = ''

    @property
    def IsValid(self):
        return not self.Error

    def initializeSession(self, scheme, name):
        session = getSession(self.ctx, scheme, name)
        if session:
            self.Session = session
        else:
            self.Error = "ERROR: Can't initialize user's session: %s from provider" % name

    def getSessionMode(self, host):
        return getSessionMode(self.ctx, host)

    def execute(self, parameter):
        return execute(self.Session, parameter)

    def getEnumerator(self, parameter):
        return Enumerator(self.Session, parameter)

    def getInputStream(self, parameter, chunk, buffer):
        return InputStream(self.Session, parameter, chunk, buffer)

    def getOutputStream(self, parameter, size, chunk, response):
        response = uno.createUnoStruct('com.sun.star.beans.Optional<com.sun.star.ucb.XRestKeyMap>')
        output = OutputStream(self.Session, parameter, size, chunk, response)
        return output, response
