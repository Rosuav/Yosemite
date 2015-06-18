#!/usr/bin/env pike
//Turn the screen off promptly once VLC Media Player isn't running, and
//turn it on again as soon as VLC appears to be running again.
//Currently just polls for a running process - inefficient but simple.
//Tying in with the main Yosemite engine might work better for screen on.

int main(int argc,array(string) argv)
{
	if (argc<2) exit(1,"USAGE: %s output_to_operate\nOr run 'sudo %<s install output_to_operate' to create a systemd service.\n",argv[0]);
	if (argc>2 && argv[1]=="install")
	{
		Stdio.write_file("/etc/systemd/system/screenblank.service",sprintf(#"[Unit]
Description=Yosemite Screen Blanker

[Service]
Environment=DISPLAY=%s
User=%s
ExecStart=%s %s
",getenv("DISPLAY"),getenv("SUDO_USER"),argv[0],argv[2]));
		exit(0,"Installed as screenblank.service\n");
	}
	string output=argv[1];
	int state=-1;
	while (1)
	{
		sleep(2);
		int running=has_value(Process.run(({"ps","-A"}))->stdout,"vlc");
		if (running==state) continue;
		state=running;
		Process.create_process(({"xrandr","--output",output,state?"--auto":"--off"}))->wait();
	}
}
