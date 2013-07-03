__author__ = "David Rusk <drusk@uvic.ca>"

import os

from ossos import storage


class LocalDirectoryWorkingContext(object):
    def __init__(self, directory):
        self.directory = directory

    def get_listing(self, suffix):
        return listdir_for_suffix(self.directory, suffix)

    def get_full_path(self, filename):
        return os.path.join(self.directory, filename)

    def get_file_size(self, filename):
        return os.stat(self.get_full_path(filename)).st_size

    def open(self, filename, mode):
        return storage.open_vos_or_local(self.get_full_path(filename), mode)

    def exists(self, filename):
        return os.path.exists(self.get_full_path(filename))

    def rename(self, old_name, new_name):
        os.rename(self.get_full_path(old_name), self.get_full_path(new_name))

    def remove(self, filename):
        os.remove(self.get_full_path(filename))


def listdir_for_suffix(directory, suffix):
    """Note this returns file names, not full paths."""
    return filter(lambda name: name.endswith(suffix), os.listdir(directory))
