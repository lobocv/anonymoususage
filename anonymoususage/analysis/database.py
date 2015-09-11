__author__ = 'calvin'

import sqlite3
import logging
from collections import defaultdict
from anonymoususage.tools import *

logger = logging.getLogger('AnonymousUsage')


class DataBase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super(DataBase, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row
        self.uuids = {}
        self.tables = defaultdict(dict)
        self.stat_totals = defaultdict(int)
        self.load_table_info()

    def rename_table(self, original, new):
        """
        Rename a table in the database.
        """
        try:
            rename_table(self, original, new)
            self.tables[new] = self.tables.pop(original)
            for uuid, info in self.uuids.iteritems():
                info[new] = info.pop(original)
        except sqlite3.OperationalError as e:
            logger.error(e)

    def load_table_info(self):
        """
        Load a summary of the databases tables sorted by table name and uuid.
        """
        self.tables.clear()
        self.stat_totals.clear()
        table_names = get_table_list(self)
        for uuid in get_uuid_list(self):
            self.uuids[uuid] = {table: get_number_of_rows(self, table, uuid=uuid) for table in table_names}
        for table in table_names:
            for uuid, info in self.uuids.iteritems():
                self.stat_totals[table] += info.get(table, 0)
                self.tables[table][uuid] = info.get(table, 0)
