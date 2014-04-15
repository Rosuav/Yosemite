/*
Authorization manager for Yosemite

Run this (as root) to accept keys for sshfs. Once this is running, anyone with
HTTP access can begin using the Yosemite Project as follows:

$ wget hostname/yos
(where 'hostname' is the name of this host, eg huix)
$ chmod +x yos
$ ./yos

TODO: Make this more generic. It's currently specific to my own LAN.

Setup:
* Create new account 'yosemite', create .ssh/authorized_keys, clean out everything else in ~ and mark it all read-only except authorized_keys itself
* Ensure that acct yosemite has read-only access to /video

*/

void request(Protocols.HTTP.Server.Request req)
{
	switch (req->not_query)
	{
		//Return the script used for connecting.
		case "/yos": req->response_and_finish((["data":
#"#!/bin/bash
cd
# Ensure we have a keypair to use
[ -d .ssh ] || mkdir .ssh
[ -f .ssh/id_rsa.pub ] || ssh-keygen -f .ssh/id_rsa -N '' -q
# Try to make the mount point, if possible. (This really ought to be
# somewhere else, but I don't want to break backward compat on the LAN.)
[ -d /video ] || mkdir /video 2>/dev/null || { sudo mkdir /video 2>/dev/null && sudo chown $USER: /video; }
# Try to authenticate with the server, logging to .yos_authority
# If the authentication fails or is revoked, remove that file to re-attempt.
[ -f .yos_authority ] || wget huix/.yos_authority --post-file .ssh/id_rsa.pub -q
sshfs yosemite@huix:/video/ /video
cd /video
python Yosemite.py
"])); break;
		case "/.yos_authority": if (req->body_raw!="")
		{
			//TODO: Check for duplicates (maybe by ignoring the key and
			//just replacing anything with the same "user@host" tail).
			Stdio.append_file("/home/yosemite/.ssh/authorized_keys",String.trim_all_whites(req->body_raw)+"\n");
			req->response_and_finish((["data":"Authenticated at "+ctime(time())]));
			break;
		}
		default: req->response_and_finish((["data":"Not found.","error":404]));
	}
}

int main()
{
	Protocols.HTTP.Server.Port(request);
	//TODO: Drop privileges
	return -1;
}
