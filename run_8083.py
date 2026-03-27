import sys

sys.path.insert(0, 'server')
from app import AppHandler, HTTPServer

server = HTTPServer(('127.0.0.1', 8083), AppHandler)
print('Listening on 8083', flush=True)
server.serve_forever()
