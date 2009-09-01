The code consists of the following packages:

- ace: This is the main package, which contains the correlation engine. 

- ace-webui: This a web interface to the correlation engine. It is written in
  Python using lxml. Although it was created for demonstration purposes only,
  it should be stable. To run it, ace must be started with an RPC server on
  localhost:1070 (HOST and PORT can be adjusted in index.py). Furthermore, a
  webserver, which considers .py files as CGI scripts must be started in
  ace-webui or a parent directory (e.g. thttpd -p 1080 -T utf-8 -c "**.py").

- ace-websink: This is a web event sink (event viewer). It is written in
  JavaScript using JQuery. It was written for demonstration purposes only and
  is likely not very stable. To run it, ace must be started using an RPC
  server *as event sink* on localhost:1071 (can be adjusted in event.py). Just
  like above, a webserver for .py CGI scripts is needed.

All packages require Python 2.6 for execution (earlier versions produce in
syntax errors, which can not be provented), and the PYTHONPATH environment
variable must be set to the parent directory (code), which contains the
packages. Furthermore, the DTDs for rules and events are required in the
locations specified in the configuration file, as well as in the locations
specified in the rule file itself.
