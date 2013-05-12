# Yosemite Project: web-invokable multimedia
# Designed for an embedded system that controls a home theatre.
# For full functionality, requires either:
#   For Windows: the Python win32api module from the Python for Windows extensions
#       http://starship.python.net/~skippy/win32/
#   For Linux using GNOME: the "Crikey" key sender:
#       http://www.shallowsky.com/software/crikey/ (you'll need to build it)
# If there is a file called 00index.txt in a directory, it will be displayed in the directory listing.
# Directories that look like DVDs (those that have a VIDEO_TS subfolder) will be treated as invokable.

import os
try:
	from urllib.parse import unquote # Python 3
except ImportError:
	from urllib import unquote # Python 2
try:
	import http.server as BaseHTTPServer # Python 3
except ImportError:
	import BaseHTTPServer # Python 2
import xml.sax.saxutils
from config import * # Get the user config (see config.py)

try:
	FileNotFoundError
except NameError:
	FileNotFoundError=OSError

if usevnc: # Send keys via VNC. Works on any platform, as long as there's a VNC server running.
	print("Connecting to VNC")
	import socket
	vnc=socket.socket()
	vnc.connect(("127.0.0.1",5900))
	vnc.send(vnc.recv(12)) # Handshake
	vnc.recv(16); vnc.send("\1"); vnc.recv(16) # Auth (no auth)
	vnc.send("\1"); vnc.recv(256) # Shared mode
	def dokey(key1,key2=None):
		vnc.send("\4\1\0\0\0\0"+key1) # Modifier down (or key down, if no modifier)
		if key2!=None:
			vnc.send("\4\1\0\0\0\0"+key2) # Key down
			vnc.send("\4\0\0\0\0\0"+key2) # Key up
		vnc.send("\4\0\0\0\0\0"+key1) # Modifier up
	shift="\xff\xe1"; ctrl="\xff\xe3"; left="\xff\x51"; right="\xff\x53"; space="\x00\x20"
	print("VNC connection established.")
	keysender="VNC"
else: # Try some platform-specific methods.
	try:
		# Do it with the win32api module. Works, obviously, only on Windows.
		import win32api
		def dokey(key1,key2=None):
			win32api.keybd_event(key1,0,0,0)
			if key2!=None:
				win32api.keybd_event(key2,0,0,0)
				win32api.keybd_event(key2,0,2,0)
			win32api.keybd_event(key1,0,2,0)
		shift=16; ctrl=17; left=37; right=39; space=32
		keysender="keybd_event"
	except: # TODO: Un-bare this except
		# No win32api. Try crikey.
		if os.system('crikey')==0:
			def dokey(key1,key2=""):
				os.system("crikey '"+key1+key2+"'")
			shift="\\S"; ctrl="\\C"; left="\\(Left\\)"; right="\\(Right\\)"; space=" "
			keysender="crikey"
		else:
			def dokey(key1,key2=None):
				pass # No key sending available
			print("Unable to send keys.")
			keysender="no key sender"

if invokecmd!=None:
	def invoke(object):
		os.system(invokecmd%object)
	invoker="defined command"
else:
	try:
		import win32api
		def invoke(object):
			win32api.ShellExecute(0,None,object,None,None,0)
		invoker="ShellExecute"
	except: # TODO: Un-bare this except
		if os.system('gnome-open')==256: # This will produce some screen output. I don't really care. (Redirecting STDERR to the null device is either "2>nul" or "2>/dev/null" but how can I tell which?)
			def invoke(object):
				os.system("gnome-open '"+object.replace("'",r"'\''")+"'")
				if keysender=="crikey": os.system("crikey -s 1 '\27f'");
			invoker="gnome-open"
		else:
			print("Unable to invoke movies.")
			invoker="no invoker"

print("Using %s and %s"%(invoker,keysender))

class VideosHTTP(BaseHTTPServer.BaseHTTPRequestHandler):
	def noresp(self):
			self.send_response(200)
			self.send_header("Content-type","text/plain")
			self.send_header("Content-length",0)
			self.end_headers()
			# self.wfile.close()

	def do_GET(self):
		# print self.path
		if self.path=="/fwd1":
			dokey(shift,right)
			self.noresp()
			return
		if self.path=="/fwd2":
			dokey(ctrl,right)
			self.noresp()
			return
		if self.path=="/back1":
			dokey(shift,left)
			self.noresp()
			return
		if self.path=="/pause":
			dokey(space)
			self.noresp()
			return
		if self.path=="/back2":
			dokey(ctrl,left)
			self.noresp()
			return
		if self.path=="/stop":
			if abortcmd!=None:
				os.system(abortcmd)
			self.noresp()
			return
		# Base path is actually used only once.
		realpath=os.path.join(basepath,unquote(self.path[1:]).replace("/",os.sep))
		try:
			os.stat(realpath)
			if not realpath.endswith(os.sep) and os.path.isdir(realpath):
				realpath=realpath+os.sep
				self.path=self.path+"/"
		except FileNotFoundError:
			# File not found --> 404 Not Found. A perfect match.
			self.send_response(404)
			self.send_header("Content-type","text/plain")
			self.end_headers()
			self.wfile.write(b"Not found, sorry mate!\r\n")
			return
		if realpath.endswith(os.sep):
			if os.path.isdir(os.path.join(realpath,"VIDEO_TS")):
				if dvdcmd!=None:
					os.system(dvdcmd%realpath[:-1])
				else:
					invoke(realpath)
				self.noresp()
				return
			self.send_response(200)
			self.send_header("Content-type","text/html")
			self.end_headers()
			self.wfile.write(
b"""<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Videos</title>
<script type="text/javascript">
function docmd(c)
{
	document.getElementById("discard").src="/"+c;
}
</script>
</head>
<body>
<div style="position:fixed; right:10px; background-color:0f0"">
<div>
<input type="button" value="&lt;&lt;" onclick="docmd('back2')">
<input type="button" value="&lt;" onclick="docmd('back1')">
<input type="button" value="||" onclick="docmd('pause')">
<input type="button" value="&gt;" onclick="docmd('fwd1')">
<input type="button" value="&gt;&gt;" onclick="docmd('fwd2')">
</div>
<div>
<input type="button" value="Stop all" onclick="docmd('stop')">
</div>
</div>
<ul>
""")
			(path,dirs,files)=next(os.walk(realpath))
			dirs.sort(key=str.lower);
			if self.path!='/': dirs.insert(0,"..")
			for d in dirs:
				if os.path.isdir(os.path.join(realpath,d,"VIDEO_TS")):
					files.append(d+"/")
				else:
					self.wfile.write(('<li><a href="%s%s/">%s/</a></li>\n'%(self.path,d,d)).encode('UTF-8'))
			files.sort(key=str.lower)
			self.wfile.write(b"</ul><ul>")
			index=None
			for f in files:
				if f=='00index.txt':
					index=open(os.path.join(realpath,f)).read()
				else:
					self.wfile.write(('<li><a href="%s%s" target="discard">%s</a></li>\n'%(self.path,f,f)).encode('UTF-8'))
			self.wfile.write(b"\n</ul>\n")
			if index!=None:
				self.wfile.write(b'<div style="background-color: #ddf; margin: 0 100px 0 100px">'
					+xml.sax.saxutils.escape(index).replace("\r","").replace("\n","<br>").encode('UTF-8')
					+b'</div>')
			self.wfile.write(
b"""
<iframe name="discard" id="discard" frameborder="0" width="0" height="0">&nbsp;</iframe>
</body>
</html>
""")
			return
		invoke(realpath)
		self.noresp()
		return

	server_version="Videos/0.1"

try:
	server=BaseHTTPServer.HTTPServer(("",port),VideosHTTP)
	print("Server active");
	server.serve_forever();
except KeyboardInterrupt:
	server.socket.close()
print("Server terminated.")
