#!/bin/bash

WorkBench=CloudUcpOOo
OOoProgram=/usr/lib/libreoffice/program
Path=$(dirname "${0}")

rm ${Path}/${WorkBench}/types.rdb

./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestDataSourceSyncMode
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestRequestTokenType
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestRequestToken
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestRequestEnumerator
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestRequestParameter
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestKeyMap
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestProvider
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestProvider
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestRequest
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestDataSource
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestUser
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestIdentifier
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestContent
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/XRestContentProvider
./rdb/make_rdb.sh ${WorkBench} com/sun/star/ucb/RestContentProvider

read -p "Press enter to continue"

${OOoProgram}/regview ${Path}/${WorkBench}/types.rdb
