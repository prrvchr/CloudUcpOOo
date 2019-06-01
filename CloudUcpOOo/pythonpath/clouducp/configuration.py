#!
# -*- coding: utf-8 -*-

# General configuration
g_identifier = 'com.gmail.prrvchr.extensions.CloudUcpOOo'

# Request / OAuth2 configuration
g_oauth2 = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
g_timeout = (15, 60)

# DataSource configuration
g_protocol = 'jdbc:hsqldb:'
g_folder = 'hsqldb'
g_jar = 'hsqldb-2.4.1.jar'
g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=true'
g_shutdow = ';shutdown=true'
