# CloudUcpOOo v.0.0.1

## Universal Content Provider offering cloud services at LibreOffice / OpenOffice.

![CloudUcpOOo screenshot](CloudUcp.png)

## This extension can not be used alone, but is necessary for the use of:

#[gDriveOOo v0.0.2] (https://github.com/prrvchr/gDriveOOo/raw/master/gDriveOOo.oxt)

#[oneDriveOOo v0.0.1] (https://github.com/prrvchr/oneDriveOOo/raw/master/oneDriveOOo.oxt)

#[DropboxOOo v0.0.1] (https://github.com/prrvchr/DropboxOOo/raw/master/DropboxOOo.oxt)

## For LibreOffice you need to configure Java User ClassPath

### Configure LibreOffice User ClassPath:

Put [hsqldb-2.4.1.jar](https://github.com/prrvchr/CloudUcpOOo/raw/master/hsqldb-2.4.1.jar) somewhere
on your hard drive.

In menu Tools - Options - LibreOffice - Advanced - Click Class Path... and Add Archive...

Add the previously downloaded archive: hsqldb-2.4.1.jar

You must restart LibreOffice for the changes to take effect
