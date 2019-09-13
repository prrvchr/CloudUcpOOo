#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier
from com.sun.star.ucb import XRestIdentifier
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.beans.PropertyAttribute import BOUND
from com.sun.star.beans.PropertyAttribute import CONSTRAINED
from com.sun.star.beans.PropertyAttribute import READONLY
from com.sun.star.beans.PropertyAttribute import TRANSIENT
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from .configuration import g_identifier
#from .content import Content

from .contenttools import getUri
from .oauth2core import getUserNameFromHandler
from .unotools import getProperty
from .unotools import getResourceLocation
from .datasourcehelper import parseDateTime
from .keymap import KeyMap

import traceback


class Identifier(unohelper.Base,
                 XContentIdentifier,
                 XRestIdentifier,
                 XChild):
    def __init__(self, ctx, user, url, contenttype=''):
        level = INFO
        msg = "Identifier loading"
        self.ctx = ctx
        self.User = user
        self._Url = self._getUrl(url)
        self._ContentType = contenttype
        self._Error = ''
        self.MetaData = KeyMap()
        msg += " ... Done"
        self.Logger.logp(level, "Identifier", "__init__()", msg)

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('Id', None)
    @property
    def IsRoot(self):
        return self.MetaData.getDefaultValue('IsRoot', False)
    @property
    def IsValid(self):
        return all((not self.Error, self.Id))
    @property
    def IsNew(self):
        return self.MetaData.getValue('IsNew')
    @property
    def BaseURI(self):
        return self.MetaData.getValue('BaseURI')
    @property
    def BaseURL(self):
        return self.MetaData.getValue('BaseURL')
    @property
    def Logger(self):
        return self.User.DataSource.Logger
    @property
    def Error(self):
        return self.User.Error if self.User.Error else self._Error

    def initialize(self, name):
        try:
            print("Identifier.initialize() 1")
            url = self.getContentIdentifier()
            uri = getUri(self.ctx, url)
            if not uri:
                self._Error = "Can't parse Uri from Url: %s" % url
                return False
            print("Identifier.initialize() 2 %s - %s" % (uri.hasAuthority(),uri.getPathSegmentCount()))
            if not uri.hasAuthority() or not uri.getPathSegmentCount():
                self._Error = "Can't retrieve User from Url: %s" % url
                return False
            name = self._getUserName(uri, name)
            if not self.User.initialize(name):
                return False
            paths = []
            position = -1
            basename = ''
            isroot = False
            isfolder = False
            isnew = self._ContentType != ''
            for i in range(uri.getPathSegmentCount() -1, -1, -1):
                path = uri.getPathSegment(i).strip()
                if path not in ('','.'):
                    if not basename:
                        basename = path
                        position = i
                        break
            for i in range(position):
                paths.append(uri.getPathSegment(i).strip())
            if isnew:
                id = self.User.getNewIdentifier()
                isfolder = self.DataSource.Provider.isFolder(self._ContentType)
            elif not basename:
                id = self.User.RootId
                isroot = True
                isfolder = True
            elif self.User.isIdentifier(basename):
                id = basename
                isfolder = True
            else:
                id = self._searchId(paths[::-1], basename)
            paths.insert(0, uri.getAuthority())
            baseuri = '%s://%s' % (uri.getScheme(), '/'.join(paths))
            self.MetaData.insertValue('BaseURI', baseuri)
            if not id:
                self._Error = "ERROR: Can't retrieve Uri: %s" % uri.getUriReference()
                return False
            uname = id if isfolder else basename
            baseurl = baseuri if isroot else '%s/%s' % (baseuri, uname)
            self.MetaData.insertValue('BaseURL', baseurl)
            self.MetaData.insertValue('Id', id)
            self.MetaData.insertValue('IsRoot', isroot)
            self.MetaData.insertValue('IsNew', isnew)
            self.MetaData.insertValue('BaseName', basename)
            print("Identifier.initialize() 2")
            return True
        except Exception as e:
            print("Identifier.initialize() ERROR: %s - %s" % (e, traceback.print_exc()))

    def getContent(self):
        if self.IsNew:
            timestamp = parseDateTime()
            isfolder = self.User.DataSource.Provider.isFolder(self._ContentType)
            isdocument = self.User.DataSource.Provider.isDocument(self._ContentType)
            data = KeyMap()
            data.insertValue('Id', self.Id)
            data.insertValue('ContentType', self._ContentType)
            data.insertValue('DateCreated', timestamp)
            data.insertValue('DateModified', timestamp)
            mediatype = self._ContentType if isfolder else ''
            data.insertValue('MediaType', mediatype)
            data.insertValue('Size', 0)
            data.insertValue('Trashed', False)
            data.insertValue('CanAddChild', True)
            data.insertValue('CanRename', True)
            data.insertValue('IsReadOnly', False)
            data.insertValue('IsVersionable', False)
            data.insertValue('Loaded', True)
            data.insertValue('IsFolder', isfolder)
            data.insertValue('IsDocument', isdocument)
        else:
            data = self.User.getItem(self.MetaData)
        data.insertValue('BaseURI', self.MetaData.getValue('BaseURI'))
        service = '%s.Content' % g_identifier
        content = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        content.initialize(self, data)
        return content

    def setTitle(self, title, isfolder):
        basename = self.Id if isfolder else title
        self.MetaData.insertValue('BaseName', basename)
        baseurl = '%s/%s' % (self.BaseURI, basename)
        self.MetaData.insertValue('BaseURL', baseurl)
        return title

    def insertNewDocument(self, content):
        parentid = self.getParent().Id
        return self.User.insertNewDocument(self.Id, parentid, content)
    def insertNewFolder(self, content):
        parentid = self.getParent().Id
        return self.User.insertNewFolder(self.Id, parentid, content)

    def isChildId(self, title):
        return self.User.isChildId(self.Id, title)
    def selectChildId(self, title):
        return self.User.selectChildId(self.Id, title)
    def countChildTitle(self, title):
        return self.User.countChildTitle(self.Id, title)

    def updateTrashed(self, value, default):
        parentid = self.getParent().Id
        return self.User.updateTrashed(self.Id, parentid, value, default)
    def updateTitle(self, value, default):
        parentid = self.getParent().Id
        return self.User.updateTitle(self.Id, parentid, value, default)

    def getInputStream(self, path, id):
        url = '%s/%s' % (path, id)
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    # XRestIdentifier
    def createNewIdentifier(self, contenttype):
        return Identifier(self.ctx, self.User, self.BaseURL, contenttype)

    def getDocumentContent(self, sf, content, size):
        size = 0
        url = '%s/%s' % (self.User.DataSource.Provider.SourceURL, self.Id)
        if content.getValue('Loaded') == OFFLINE and sf.exists(url):
            size = sf.getSize(url)
            return url, size
        stream = self.User.DataSource.Provider.getDocumentContent(content)
        if stream:
            try:
                sf.writeFile(url, stream)
            except Exception as e:
                msg = "ERROR: %s - %s" % (e, traceback.print_exc())
                self.Logger.logp(SEVERE, "Identifier", "getDocumentContent()", msg)
            else:
                size = sf.getSize(url)
                loaded = self.User.updateLoaded(self.Id, OFFLINE, ONLINE)
                content.insertValue('Loaded', loaded)
            finally:
                stream.closeInput()
        return url, size

    def getFolderContent(self, content):
        select, updated = self.User.getFolderContent(self.MetaData, content, False)
        if updated:
            loaded = self.User.updateLoaded(self.Id, OFFLINE, ONLINE)
            content.insertValue('Loaded', loaded)
        return select

    # XContentIdentifier
    def getContentIdentifier(self):
        return self._Url
    def getContentProviderScheme(self):
        return self.User.DataSource.Provider.Scheme

    # XChild
    def getParent(self):
        url = '%s/' % self.BaseURI
        print("Identifier.getParent() 1 %s" % url)
        parent = Identifier(self.ctx, self.User, url)
        if parent.initialize(self.User.Name):
            print("Identifier.getParent() 2 %s" % parent.Id)
            return parent
        print("Identifier.getParent() 3 ************")
        return None
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    def _getUrl(self, identifier):
        url = uno.createUnoStruct('com.sun.star.util.URL')
        url.Complete = identifier
        transformer = self.ctx.ServiceManager.createInstance('com.sun.star.util.URLTransformer')
        success, url = transformer.parseStrict(url)
        if success:
            identifier = transformer.getPresentation(url, True)
        return identifier

    def _getUserName(self, uri, name):
        if uri.hasAuthority() and uri.getAuthority() != '':
            name = uri.getAuthority()
            print("Identifier._getUserName(): uri.getAuthority() = %s" % name)
        elif name == '':
            message = "Authentication"
            scheme = self.getContentProviderScheme()
            name = getUserNameFromHandler(self.ctx, self, scheme, message)
            print("Identifier._getUserName(): getUserNameFromHandler() = %s" % name)
        print("Identifier._getUserName(): %s" % name)
        return name

    def _searchId(self, paths, basename):
        # Needed for be able to create a folder in a just created folder...
        id = ''
        paths.append(self.User.RootId)
        for i, path in enumerate(paths):
            if self.User.isIdentifier(path):
                id = path
                break
        for j in range(i -1, -1, -1):
            id = self.User.selectChildId(id, paths[j])
        id = self.User.selectChildId(id, basename)
        return id

