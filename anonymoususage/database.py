__author__ = 'calvin'

import sqlite3

from tools import *


class DataBase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super(DataBase, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row
        table_names = get_table_list(self)
        uuid_list = get_uuid_list(self)
        self.uuids = {}
        for uuid in uuid_list:
            self.uuids[uuid] = {table: get_number_of_rows(self, table, uuid=uuid) for table in table_names}
