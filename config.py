# Example configuration for a Linux system. Change these variables to suit your situation.
port=3003 # TCP port to bind to
usevnc=False  # Set to True to use a VNC connection to send keys. Requires a VNC server on the same computer, running with authentication disabled.
invokecmd=None # By default, attempt to detect an invocation method.
# Or set it to a full command such as this. Use %s for the file name.
# invokecmd='vlc "%s"'
# dvdcmd=None # By default, DVD folders will use the same invocation method as ordinary files (whether detected or explicit command).
dvdcmd='vlc -f dvdsimple://"%s" >/dev/null 2>/dev/null &'
# As above, the 'Play All' command by default is the same invocation as individual files.
playallcmd='vlc "%s" &'
abortcmd='killall totem; killall vlc' # Execute this to kill all video players. Hmm. There's a pun in there, or I'm much mistaken.
basepath=r"/video"  # Base path to all videos. Note that this does not chroot or anything, and is not guaranteed to prevent all possible ways "out" of the "jail".
