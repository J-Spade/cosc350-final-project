import BaseHTTPServer
import cgi
import os

webpage_text = ''

class MarkovReqHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write('<html><body><form action="/" method="POST"><input type="text" name="text"><input type="submit" value="send"></form></body></html>')

    def do_HEAD(self):
        self._set_headers()
    
    def do_POST(self):
        form = cgi.FieldStorage(
                fp = self.rfile,
                headers = self.headers,
                environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']
                          })

        self._set_headers()
        message = ''
        if (len(form) > 0):
            message = form['text'].value
        self.wfile.write(str.replace(webpage_text, message))


def runserver(server_class=BaseHTTPServer.HTTPServer,
        handler_class=MarkovReqHandler,
        port=int(os.environ.get('PORT', 5000))):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print 'starting httpd...'
    httpd.serve_forever()

try:
    webpage = open('chatbox.html', 'r')
    webpage_text = webpage.read()
    webpage.close()
except IOError:
    print 'unable to load chat page'

runserver()