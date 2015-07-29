__author__ = 'calvin'

import sqlite3

from tools import *


class DataBase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super(DataBase, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row
        self.tables = get_table_list(self)
        sd=3
