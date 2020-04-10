FIX FILE WATCHER
===============

This a simple fix to a unbearable default solution of google-cloud-sdk for the autoreload function of the `dev_appserver`.
Indeed google decided to default to a pooling thread that consistently uses tons of CPU to check of the files of the project have ben edited

So, to fi that, you just need to use this simple script, that will replace the default file_watcher implementation of the SDK, and replace it by 
a way more simpler version based on [watchdog](https://github.com/gorakhargosh/watchdog) 

HOW TO INSTALL
-------------

As simple as:
```shell script
python fix_wacther
```

By default, it will assume that the sdk is installed at 
```text
/home/user/google-cloud-sdk
```

Here all this too can do:
```console
foo@bar:~$ python fix_watcher -h
usage: fix_watcher.py [-h] [-t PATH] [--uninstall] [-f PATH]

Will install watchdog into local google-appengine-sdk and use it to improve
performances

optional arguments:
  -h, --help            show this help message and exit
  -t PATH, --to PATH    PATH to the google cloud SDK
  --uninstall           removes watchdog and restores files to original state
  -f PATH, --from PATH  PATH to the google cloud SDK to uninstall. By default
                        will reuse PATH from last install
```
Set SDK location
----------------

```shell script
GOOGLE_SDK_PATH='/path/to/sdk python'
python fix_wacther --target $GOOGLE_SDK_PATH
```
Configuration
------------

You can configure teh file watcher by adding these options in you `Setup.cgf`
```ini
[appengine:file_watcher]
watcher_extension=.js,.html,.css,.py
```

With each option being:

| Option              | Definition                       | Default Value |
| ------------------- | -------------------------------- | --- |
| `watcher_extension` | list of `.ext` separated by a `,`| `.go,.py,.yaml` ([see mtime_file_watcher](https://github.com/anis-campos/fix-gcp-file-watcher/blob/master/fix/mtime_file_watcher.py#L21))|
| | | |
