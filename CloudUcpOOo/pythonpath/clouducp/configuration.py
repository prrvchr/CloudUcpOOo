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
g_jar = 'hsqldb.jar'
g_class = 'org.hsqldb.jdbcDriver'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=false'
g_shutdow = ';shutdown=true'
