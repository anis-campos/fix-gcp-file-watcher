#!/usr/bin/env python
#
# Replacement `MtimeFileWatcher` for App Engine SDK's dev_appserver.py,
# designed for OS X. Improves upon existing file watcher (under OS X) in
# numerous ways:
#
#   - Uses watchdog.events to watch for changes instead of polling. This saves a
#     dramatic amount of CPU, especially in projects with several modules.
#   - Tries to be smarter about which modules reload when files change, only
#     modified module should reload.
#
import logging
import os
import time
from ConfigParser import ConfigParser, NoSectionError

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

# Only watch for changes to .go, .py or .yaml files
WATCHED_EXTENSIONS = {'.go', '.py', '.yaml'}


def get_watched_extensions():
    """
    Gets extension from configuration, or return WATCHED_EXTENSIONS
    Returns:

    """

    def find_upwards(file_name, start_at=os.getcwd()):
        """
        Look up for a file, in a folder and parent folders
        Args:
            file_name(str): file name to look for
            start_at(str): starting point, Default is current working dir

        Returns:
            (str): file absolute path if found, none otherwise
        """
        cur_dir = start_at
        while True:
            file_list = os.listdir(cur_dir)
            parent_dir = os.path.dirname(cur_dir)
            if file_name in file_list:
                return cur_dir
            else:
                if cur_dir == parent_dir:
                    return None
                else:
                    cur_dir = parent_dir

    watched_extensions = WATCHED_EXTENSIONS
    setup_cfg_path = find_upwards("setup.cfg")
    if setup_cfg_path:
        config = ConfigParser()
        try:
            config_value = config.get('appengine:file_watcher', 'watched_extensions')
            watched_extensions = set(config_value)
        except (NoSectionError, TypeError):
            watched_extensions = WATCHED_EXTENSIONS

    return watched_extensions


class FileWatcher(object):
    """
    FileWatcher interface using Watchdog Observer
    """

    def __init__(self, directories, **kwargs):
        # Path to current module
        self.module_dir = directories[0]
        self._changes = []

        self.observer = Observer()
        self.observer.schedule(self, self.module_dir, recursive=True)

    def start(self):
        self.observer.start()

    def changes(self, *args):
        time.sleep(1)
        changed = set(self._changes)
        del self._changes[:]
        return changed

    def quit(self):
        # noinspection PyBroadException
        try:
            self.observer.stop()
        except Exception:
            logging.exception("can't stop observer")


class MtimeFileWatcher(FileWatcher, PatternMatchingEventHandler):
    """
    Replacing pooling all files by file events and pattern matching
    """
    SUPPORTS_MULTIPLE_DIRECTORIES = True

    def __init__(self, directories, **kwargs):
        FileWatcher.__init__(self, directories, **kwargs)

        watched_extensions = get_watched_extensions()

        # pattern matching files with extension
        patterns = ["*{}".format(ext) for ext in watched_extensions]
        logging.info("Stating fs watching on {} with pattern:{}".format(self.module_dir, patterns))

        PatternMatchingEventHandler.__init__(self, patterns=patterns)

    def on_any_event(self, event):
        """
        Called on file moved, created, deleted, modified events
        """
        self._changes.append(event.src_path)
