__author__ = 'calvin'

import sqlite3

from collections import defaultdict
from tools import *


class DataBase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super(DataBase, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row
        table_names = get_table_list(self)
        uuid_list = get_uuid_list(self)
        self.uuids = {}
        self.tables = defaultdict(dict)
        self.stat_totals = defaultdict(int)
        for uuid in uuid_list:
            self.uuids[uuid] = {table: get_number_of_rows(self, table, uuid=uuid) for table in table_names}
        for table in table_names:
            for uuid, info in self.uuids.iteritems():
                self.stat_totals[table] += info.get(table, 0)
                self.tables[table][uuid] = info.get(table, 0)
