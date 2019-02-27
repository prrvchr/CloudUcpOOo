#!/bin/bash

cd ./CloudUcpOOo/

zip -0 CloudUcpOOo.zip mimetype

zip -r CloudUcpOOo.zip *

cd ..

mv ./CloudUcpOOo/CloudUcpOOo.zip ./CloudUcpOOo.oxt
