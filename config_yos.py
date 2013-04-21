# Configuration. Change these variables to suit your system.
port=3003 # TCP port to bind to
usevnc=False  # Set to True to use a VNC connection to send keys. Requires a VNC server on the same computer, running with authentication disabled.
invokecmd=None # By default, attempt to detect an invocation method.
# Or set it to a full command such as this. Use %s for the file name.
invokecmd='start "Movie Player" "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe" -f "%s"'
dvdcmd=None # By default, DVD folders will use the same invocation method as ordinary files (whether detected or explicit command).
dvdcmd='start "Movie Player" "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe" -f dvdsimple://"%s"'
# dvdcmd='vlc -f dvdsimple://"%s" >/dev/null 2>/dev/null &'
abortcmd='taskkill /im vlc.exe' # Execute this to kill all video players. Hmm. There's a pun in there, or I'm much mistaken.
basepath=r"\\huix\video"  # Base path to all videos. Note that this does not chroot or anything, and is not guaranteed to prevent all possible ways "out" of the "jail".
# End of config options. Below here shouldn't need to be changed.
