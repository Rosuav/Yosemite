# Yosemite Project: web-invokable multimedia
# Designed for an embedded system that controls a home theatre.
# For full functionality, requires either:
#   For Windows: the Python win32api module from the Python for Windows extensions
#       http://starship.python.net/~skippy/win32/
#   For Linux using GNOME: the "Crikey" key sender:
#       http://www.shallowsky.com/software/crikey/ (you'll need to build it)
# If there is a file called 00index.txt in a directory, it will be displayed in the directory listing.
# Directories that look like DVDs (those that have a VIDEO_TS subfolder) will be treated as invokable.
# Requires Python 3.4 or greater (I think - untested on 3.3).

import os
import json
from subprocess import Popen
import collections
from urllib.parse import quote, unquote
from http.server import BaseHTTPRequestHandler, HTTPServer
import xml.sax.saxutils
from config import * # Get the user config (see config.py)

if usevnc: # Send keys via VNC. Works on any platform, as long as there's a VNC server running.
	print("Connecting to VNC")
	import socket
	vnc=socket.socket()
	vnc.connect(("127.0.0.1", 5900))
	vnc.send(vnc.recv(12)) # Handshake
	vnc.recv(16); vnc.send("\1"); vnc.recv(16) # Auth (no auth)
	vnc.send("\1"); vnc.recv(256) # Shared mode
	def dokey(key1, key2=None):
		vnc.send("\4\1\0\0\0\0" + key1) # Modifier down (or key down, if no modifier)
		if key2 is not None:
			vnc.send("\4\1\0\0\0\0" + key2) # Key down
			vnc.send("\4\0\0\0\0\0" + key2) # Key up
		vnc.send("\4\0\0\0\0\0" + key1) # Modifier up
	shift, ctrl, left, right, space = "\xff\xe1", "\xff\xe3", "\xff\x51", "\xff\x53", "\x00\x20"
	print("VNC connection established.")
	keysender = "VNC"
else: # Try some platform-specific methods.
	try:
		# Do it with the win32api module. Works, obviously, only on Windows.
		import win32api
		def dokey(key1, key2=None):
			win32api.keybd_event(key1, 0, 0, 0)
			if key2 is not None:
				win32api.keybd_event(key2, 0, 0, 0)
				win32api.keybd_event(key2, 0, 2, 0)
			win32api.keybd_event(key1, 0, 2, 0)
		shift, ctrl, left, right, space = 16, 17, 37, 39, 32
		keysender = "keybd_event"
	except ImportError:
		# No win32api. Try crikey.
		try:
			Popen("crikey")
			# If nothing is raised, we can use crikey.
			def dokey(key1, key2=""):
				Popen(["crikey", key1+key2])
			shift, ctrl, left, right, space = "\\S", "\\C", "\\(Left\\)", "\\(Right\\)", " "
			keysender = "crikey"
		except FileNotFoundError:
			# No crikey found in system path
			def dokey(key1, key2=None):
				pass # No key sending available
			print("Unable to send keys.")
			keysender = "no key sender"

if invokecmd is not None:
	def invoke(object):
		os.system(invokecmd % object)
	invoker = "defined command"
else:
	try:
		import win32api
		def invoke(object):
			win32api.ShellExecute(0, None, object, None, None, 0)
		invoker = "ShellExecute"
	except ImportError:
		for invoker in ("xdg-open", "exo-open", "gnome-open", "kde-open", None):
			try:
				if invoker: Popen(invoker, stderr=open(os.devnull,"w"), stdout=open(os.devnull,"w"))
				break # Once one succeeds, use it.
			except FileNotFoundError:
				pass
		if invoker:
			def invoke(object):
				Popen([invoker, object])
				# Optionally send an 'f' to toggle full-screen
				# if keysender=="crikey": Popen(["crikey","-s","1","\27f"]); # I've no idea what the \27 is there for. ???
		else:
			print("Unable to invoke movies.")
			invoker = "no invoker"

print("Using %s and %s" % (invoker, keysender))

# Every file invocation gets counted. This makes for a crude popularity count,
# but note that this is not retained across server restarts.
usage = collections.Counter()

class VideosHTTP(BaseHTTPRequestHandler):
	def noresp(self):
			self.send_response(200)
			self.send_header("Content-type","text/plain")
			self.send_header("Content-length",0)
			self.end_headers()
			# self.wfile.close()

	keycmds = {
		"/fwd1": [shift, right],
		"/fwd2": [ctrl, right],
		"/back1": [shift, left],
		"/pause": [space],
		"/back2": [ctrl, left],
		"/nextsrt": ['v'],
		"/nextaud": ['b'],
	}
	def do_GET(self):
		if self.path in self.keycmds:
			dokey(*keycmds[self.path])
			self.noresp()
			return
		if self.path=="/stop":
			if abortcmd!=None:
				os.system(abortcmd)
			self.noresp()
			return
		if self.path=="/popular.json":
			self.send_response(200)
			self.send_header("Content-type","application/json")
			self.end_headers()
			self.wfile.write(json.dumps(usage).encode("ascii"))
			return
		# By default, sort by name, case-folded. Py2 doesn't have such,
		# so we just lower-case. But we might change the sort key below.
		try: sortkey = str.casefold
		except AttributeError: sortkey = str.lower
		if '?' in self.path:
			self.path, querystring = self.path.split("?", 1)
			if querystring == "popular":
				def sortkey(fn):
					return usage[os.path.join(realpath,fn)], fn.lower()
		# Base path is actually used only once.
		realpath=os.path.join(basepath,unquote(self.path[1:]).replace("/",os.sep))
		if realpath.endswith('*'):
			if playallcmd is not None:
				os.system(playallcmd%realpath[:-1])
			else:
				invoke(realpath[:-1])
			self.send_response(301)
			self.send_header("Location", self.path[:-1])
			self.end_headers()
			return
		try:
			os.stat(realpath)
			if not realpath.endswith(os.sep) and os.path.isdir(realpath):
				self.send_response(301)
				self.send_header("Location", self.path+"/")
				self.end_headers()
				return
		except FileNotFoundError:
			# File not found --> 404 Not Found. A perfect match.
			self.send_response(404)
			self.send_header("Content-type","text/plain")
			self.end_headers()
			self.wfile.write(b"Not found, sorry mate!\r\n")
			return
		indexonly = realpath.endswith(os.sep+"00index.txt")
		if indexonly:
			realpath = realpath[:-11] # which will then go through the next block.
			self.path = self.path[:-11]
		if realpath.endswith(os.sep):
			if os.path.isdir(os.path.join(realpath,"VIDEO_TS")):
				if dvdcmd!=None:
					os.system(dvdcmd%realpath[:-1])
				else:
					usage[realpath] += 1
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
<a href="*">Play all</a>
<ul>
""")
			if indexonly:
				dirs=files=[]
			else:
				(path,dirs,files)=next(os.walk(realpath))
				dirs.sort(key=sortkey)
				dirs = [dir for dir in dirs if not dir.startswith(".")]
				files = [file for file in files if not file.startswith(".")]
				if self.path!='/': dirs.insert(0,"..")
			for d in dirs:
				if os.path.isdir(os.path.join(realpath,d,"VIDEO_TS")):
					files.append(d+"/")
				else:
					self.wfile.write(('<li><a href="%s%s/">%s/</a></li>\n'%(self.path,quote(d),d)).encode('UTF-8'))
			files.sort(key=sortkey)
			self.wfile.write(b"</ul><ul>")
			for f in files:
				if f!='00index.txt':
					self.wfile.write(('<li><a href="%s%s" target="discard">%s</a></li>\n'%(self.path,quote(f),f)).encode('UTF-8'))
			self.wfile.write(b"\n</ul>\n")
			if indexonly or '00index.txt' in files:
				self.wfile.write(b'<div style="background-color: #ddf; margin: 0 100px 0 100px">')
				with open(os.path.join(realpath,'00index.txt')) as index:
					for line in index:
						line = line.strip()
						if line.startswith("/") and os.path.exists(os.path.join(realpath, line[1:])):
							line = line[1:]
							# The line appears to be a valid file name. Turn it into a link.
							if (not os.path.isdir(os.path.join(realpath, line)) or
								os.path.isdir(os.path.join(realpath, line, "VIDEO_TS"))):
								# It's a file (possibly a DVD directory).
								line = '<a href="%s%s" target="discard">/%s</a>'%(self.path, quote(line), line)
							else:
								# It's a non-DVD directory
								line = '<a href="%s%s/">/%s/</a>'%(self.path, quote(line), line)
						line = line.encode("utf-8")
						self.wfile.write(line+b"<br>\n")
					
				self.wfile.write(b'</div>')
			self.wfile.write(
b"""
<iframe name="discard" id="discard" frameborder="0" width="0" height="0">&nbsp;</iframe>
</body>
</html>
""")
			return
		usage[realpath] += 1
		invoke(realpath)
		self.noresp()
		return

	server_version="Videos/0.1"

try:
	server=HTTPServer(("",port),VideosHTTP)
	print("Server active");
	server.serve_forever();
except KeyboardInterrupt:
	server.socket.close()
print("Server terminated.")
