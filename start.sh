#!/bin/sh

export PYTHONPATH=$PYTHONPATH:$PWD
./ace/ace $*

# webserver, e.g. (add -R above):
# thttpd -p 1080 -T utf-8 -c "**.py"
