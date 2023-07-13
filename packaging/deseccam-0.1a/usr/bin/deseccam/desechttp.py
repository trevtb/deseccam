import SimpleHTTPServer
import BaseHTTPServer
import SocketServer
import deseccamhelper
import Image
import StringIO
import time
import struct
import fcntl
import socket
import base64
import os
import signal


class ThreadedHTTP:
    sock = None
    sockfd = None
    SIOCGIFADDR = None
    interface = None
    ip = None
    port = None
    username = None
    password = None
    localonly = None
    useauthentication = None
    useaccessprotection = None
    allowedip = None
    q = None
    loggq = None
    server = None
    mainpid = None

    def __init__(self, interface, port, localonly, useauthentication, useaccessprotection,
                 allowedip, username, password, q, mainpid, loggq):
        self.interface = interface
        self.port = port
        self.q = q
        self.loggq = loggq
        self.mainpid = mainpid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockfd = self.sock.fileno()
        self.SIOCGIFADDR = 0x8915
        if not localonly:
            self.ip = self.get_ip()
        else:
            self.ip = '127.0.0.1'
        self.useauthentication = useauthentication
        self.useaccessprotection = useaccessprotection
        self.allowedip = allowedip
        self.username = username
        self.password = password

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def get_ip(self):
        ifreq = struct.pack('16sH14s', self.interface, socket.AF_INET, '\x00'*14)
        try:
            res = fcntl.ioctl(self.sockfd, self.SIOCGIFADDR, ifreq)
        except:
            return None
        return socket.inet_ntoa(struct.unpack('16sH2x4s8x', res)[2])

    def start_loop(self):
        self.server = ThreadedHTTPServer((self.ip, self.port), TimeoutHTTPRequestHandler)
        self.server.serve_forever(self.interface, self.ip, self.port, self.useauthentication, self.useaccessprotection,
                                  self.allowedip, self.username, self.password, self.q, self.mainpid, self.loggq)


class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    loggq = None

    def __init__(self, *args):
        self.daemon_threads = True
        BaseHTTPServer.HTTPServer.__init__(self, *args)

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except socket.timeout:
            self.print_and_log('Timeout during processing of request from '+str(client_address))
        except socket.error, e:
            self.print_and_log(str(e) + '(client exit?) during processing of request from '+str(client_address))
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def serve_forever(self, interface, ip, port, useauthentication, useaccessprotection, allowedip, username, password, queue, mainpid, loggq):
        self.RequestHandlerClass.interface = interface
        self.RequestHandlerClass.port = port
        self.RequestHandlerClass.q = queue
        self.loggq = loggq
        self.RequestHandlerClass.mainpid = mainpid
        self.RequestHandlerClass.ip = ip
        self.RequestHandlerClass.key = base64.b64encode(username+':'+password)
        self.RequestHandlerClass.allowip = allowedip
        self.RequestHandlerClass.useauth = useauthentication
        self.RequestHandlerClass.useaccessprotect = useaccessprotection
        BaseHTTPServer.HTTPServer.serve_forever(self)


class TimeoutHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    timeout = 2 * 60
    interface = None
    q = None
    mainpid = None
    ip = None
    port = None
    key = None
    useauth = None
    useaccessprotect = None
    allowip = None
    img = None

    def setup(self):
        self.request.settimeout(self.timeout)
        SimpleHTTPServer.SimpleHTTPRequestHandler.setup(self)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Authorization required\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.useaccessprotect and self.allowip != self.client_address[0]:
            self.wfile.write('Access denied for your ip address ' + str(self.client_address[0]))
            return

        if self.headers.getheader('Authorization') is None and self.useauth:
            self.do_AUTHHEAD()
            self.wfile.write('Access denied')
            pass
        elif self.headers.getheader('Authorization') == 'Basic ' + self.key or not self.useauth:
            if self.path.endswith('.mjpg'):
                self.send_response(200)
                self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
                self.end_headers()

                while True:
                    self.img = self.q.get()
                    jpg = Image.fromarray(deseccamhelper.CamIO.torgb(self.img))
                    tmpfile = StringIO.StringIO()
                    jpg.save(tmpfile, 'JPEG')
                    self.wfile.write("--jpgboundary")
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', str(tmpfile.len))
                    self.end_headers()
                    jpg.save(self.wfile, 'JPEG')
                    time.sleep(0.05)
                return
            elif self.path.endswith('reloadconfig.html'):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("1")
                os.kill(self.mainpid, signal.SIGHUP)
                return
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><head></head><body>')
                self.wfile.write('<img src="http://' + self.ip + ':' + str(self.port) + '/cam.mjpg"/>')
                self.wfile.write('</body></html>')
                return
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')
            pass