import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from os.path import join, exists

USER_HOME_FOLDER = os.path.expanduser("~")
DEFAULT_SDK_FOLDER = join(USER_HOME_FOLDER, "google-cloud-sdk")
CONF_FILE = join(os.getcwd(), "conf.json")
BACKUP_FOLDER = join(os.getcwd(), "backup")


def get_parser():
    """
    Argument parser to read stdin arguments
    """

    def dir_path_with_write_access(path):
        """
        Checks if arguments is a folder with write access

        Args:
            path (basestring): folder's path
        Returns:
            (str): folder's path
        Raises:
            ArgumentTypeError: if can't write to folder or folder doesn't exist
        """
        if os.path.isdir(path):
            if os.access(path, os.W_OK):
                return os.path.abspath(path)
            else:
                raise argparse.ArgumentTypeError(
                    path, "Can't write on that folder")
        else:
            raise argparse.ArgumentTypeError(
                path, "Should be a existing directory")

    parser = argparse.ArgumentParser(description='Will install watchdog into local google-appengine-sdk \
    and use it to improve performances')

    parser.add_argument('-t', '--to',
                        default=DEFAULT_SDK_FOLDER,
                        type=dir_path_with_write_access,
                        metavar="PATH",
                        help='PATH to the google cloud SDK')

    parser.add_argument('--uninstall',
                        action='store_true',
                        help='removes watchdog and restores files to original state')
    parser.add_argument('-f', '--from',
                        type=dir_path_with_write_access,
                        metavar="PATH",
                        dest="from_",
                        help='PATH to the google cloud SDK to uninstall. By default will reuse PATH from last install')
    return parser


def pip_install(package, target=None):
    """
    Calls pip and installs a package.
    Args:
        package (str): package name
        target (str): folder path where the package is to be installed

    Returns:
        (int): pip process return code
    """
    command = [sys.executable, '-m', 'pip', 'install', package]
    if target and not exists(target):
        command.extend(['--target', target])
    elif exists(target):
        logging.warn("Already installed")
        return

    return subprocess.check_call(command)


def backup(file_path):
    """
    Copy file to backup folder, enabling reset
    Args:
        file_path (str): file path
    Returns:
        (bool): True if file has been backed-up, False otherwise
    """
    filename = os.path.basename(file_path)

    if not exists(BACKUP_FOLDER):
        os.mkdir(BACKUP_FOLDER)

    dest = join(BACKUP_FOLDER, filename)
    if not exists(dest):
        logging.info("Backing up file %s to %s", file_path, dest)
        shutil.copy(file_path, dest)
        return True

    return False


def install(target_path):
    """
    Install ( if not already done ) the necessary files to the sdk directory
    Args:
        target_path (str): install directory of the sdk

    Returns:

    """
    date = datetime.now()

    app_engine = join(target_path, "platform", "google_appengine")
    app_engine_lib = join(app_engine, "lib")

    mtime_file = join(app_engine, "google", "appengine",
                      "tools", "devappserver2", "mtime_file_watcher.py")
    watchdog_path = join(app_engine_lib, "watchdog")
    pip_install("watchdog", target=watchdog_path)

    conf = {
        "last_execution": date,
        "execs": [
            {
                "target": target_path,
                "execution": date,
                "watchdog": watchdog_path
            }
        ]
    }

    backup(mtime_file)

    print("Target: {}\napp_engine:{}".format(target_path, app_engine))


def remove_folder(target_path):
    """
    Deletes a folder ( recursively )
    Args:
        target_path (str): path of folder to delete

    """
    shutil.rmtree(target_path)


def uninstall(target_path=None):
    """
    Undo the modifications
    Args:
        target_path (str): install directory of the sdk

    Returns:

    """
    if not target_path and not exists(CONF_FILE):
        logging.error("No previous install and no target !")
        return

    with open('data.txt') as json_file:
        conf = json.load(CONF_FILE)

    if not target_path:
        last_execution_date = conf["last_execution"]
        target = next((item for item in conf["execs"] if item["execution"] == last_execution_date), None)
    else:
        target = next((item for item in conf["execs"] if item["target"] == target_path), None)

    if not target:
        logging.error("can't find last install")
        return

    shutil.rmtree(target["watchdog"], ignore_errors=True)


if __name__ == '__main__':
    args = get_parser().parse_args()
    if args.uninstall:
        uninstall(args.from_)
    else:
        install(args.to)
