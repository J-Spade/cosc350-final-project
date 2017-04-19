import BaseHTTPServer
import cgi

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
        self.wfile.write('<html><body><form action="/" method="POST"><input type="text" name="text"><input type="submit" value="send"></form><br>%s</body></html>' % message)

def run(server_class=BaseHTTPServer.HTTPServer, handler_class=MarkovReqHandler, port=process.env.PORT):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'starting httpd...'
    httpd.serve_forever()

run()