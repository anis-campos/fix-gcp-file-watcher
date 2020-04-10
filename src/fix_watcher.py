import argparse
import fileinput
import glob
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
BASE_DIR = os.getcwd()
CONF_FILE = join(BASE_DIR, "conf.json")
BACKUP_FOLDER = join(os.getcwd(), "backup")


def json_dump(*args, **kwargs):
    """
    Sets the default encoding settings for json.dump
    """
    kwargs = kwargs or dict()
    kwargs.update({
        "default": str,
        "indent": 4,
        "sort_keys": True,
    })
    return json.dump(*args, **kwargs)


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


def backup(backup_path, file_path):
    """
    Copy file to backup folder, enabling reset
    Args:
        backup_path (str): backup folder path
        file_path (str): file path
    Returns:
        bool: True if file has been backed-up, False otherwise
        str: Destination path

    """
    filename = os.path.basename(file_path)

    if not exists(backup_path):
        os.mkdir(backup_path)

    dest = join(backup_path, filename)
    backed_up = False
    if not exists(dest):
        logging.info("Backing up file {} to {}".format(file_path, dest))
        shutil.copy(file_path, dest)
        backed_up = True
    else:
        logging.info("File {} already here {}".format(file_path, dest))

    return backed_up, dest


def insert_text_before_the_end(begin_str, end_str, source_file, text):
    """
    This will try to insert just before the end of the block [begin_str, end_str].

    Notes:
        Change is made in place
    Args:
        begin_str: marks the begining of the block
        end_str: marks the en of the block
        source_file: file to edit
        text: text to insert just before the end of the block
    """
    begin = False
    stop = False
    for line in fileinput.FileInput(source_file, inplace=1):
        if text in line:
            stop = True
        if begin_str in line:
            begin = True
        if not stop and begin and end_str in line:
            line = line.replace(line, text + line)
            begin = False
        print line,


def install(target_path):
    """
    Install ( if not already done ) the necessary files to the sdk directory
    Args:
        target_path (str): install directory of the sdk

    Returns:

    """
    if exists(CONF_FILE):
        with open(CONF_FILE) as json_file:
            conf = json.load(json_file)
    else:
        with open(CONF_FILE, "w") as json_file:
            conf = {}
            json_dump(conf, json_file)

    if "execs" not in conf:
        conf["execs"] = []
    if any([item for item in conf["execs"] if item["target"] == target_path]):
        logging.warn("Already installed")
        return

    app_engine = join(target_path, "platform", "google_appengine")
    app_engine_lib = join(app_engine, "lib")

    watchdog_path = join(app_engine_lib, "watchdog")
    pip_install("watchdog", target=watchdog_path)

    dev_appserver_folder = join(app_engine, "google", "appengine",
                                "tools", "devappserver2")
    mtime_file = join(dev_appserver_folder, "mtime_file_watcher.py")

    wrapper_util = join(app_engine, "wrapper_util.py")

    backup_path = join(BACKUP_FOLDER, target_path.replace(os.path.sep, "_"))
    _, mtime_file_bak = backup(backup_path, mtime_file)
    _, wrapper_util_bak = backup(backup_path, wrapper_util)

    mtime_file_fix = join(BASE_DIR, 'fix', 'mtime_file_watcher.py')

    shutil.copy(mtime_file, mtime_file_fix)

    fileList = glob.glob(dev_appserver_folder + os.path.sep + '*.pyc')
    for filePath in fileList:
        # noinspection PyBroadException
        try:
            os.remove(filePath)
        except:
            logging.exception("Error while deleting file : ", filePath)

    insert_text_before_the_end("devappserver2_paths = stub_paths + [", "]", wrapper_util,
                               "        os.path.join(dir_path, 'lib', 'watchdog'),\n")

    date = datetime.now()
    conf["last_execution"] = date

    conf["execs"].append({
        "target": target_path,
        "execution": date,
        "watchdog": watchdog_path,
        "backup_path": backup_path,
        "wrapper_util": {
            "to_replace": wrapper_util,
            "original": wrapper_util_bak,
        },
        "mtime_file": {
            "to_replace": mtime_file,
            "original": mtime_file_bak,
        }
    })
    with open(CONF_FILE, "w") as json_file:
        json_dump(conf, json_file)

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
    """
    if not target_path and not exists(CONF_FILE):
        logging.error("No previous install and no target !")
        return

    with open(CONF_FILE) as json_file:
        conf = json.load(json_file)

    if not target_path:
        last_execution_date = conf["last_execution"]
        target = next((item for item in conf["execs"] if item["execution"] == last_execution_date), None)
    else:
        target = next((item for item in conf["execs"] if item["target"] == target_path), None)

    if not target:
        logging.error("can't find last install")
        return

    shutil.rmtree(target["watchdog"], ignore_errors=True)
    shutil.copy(target["wrapper_util"]["to_replace"], target["wrapper_util"]["original"])
    shutil.copy(target["mtime_file"]["to_replace"], target["mtime_file"]["original"])
    shutil.rmtree(target["watchdog"], ignore_errors=True)
    shutil.rmtree(target["backup_path"], ignore_errors=True)

    conf["execs"].remove(target)

    with open(CONF_FILE, "w") as json_file:
        json_dump(conf, json_file)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(filename)s:%(lineno)d %(message)s')
    parsed = get_parser().parse_args()
    if parsed.uninstall:
        uninstall(parsed.from_)
    else:
        install(parsed.to)
