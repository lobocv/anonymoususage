__author__ = 'calvin'

import ftplib
import sqlite3
import logging

logger = logging.getLogger('AnonymousUsage')
logger.setLevel(logging.DEBUG)

def create_table(dbcon, name, columns):
    """
    Create a table in the database.
    :param dbcon: database
    :return: True if a new table was created
    """
    try:
        colString = ", ".join(["{} {}".format(colName, colType) for colName, colType in columns])
        dbcon.execute("CREATE TABLE {name}({args})".format(name=name, args=colString))
        return True
    except sqlite3.OperationalError as e:
        return False


def get_table_list(dbconn):
    cur = dbconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [item[0] for item in cur.fetchall()]


def get_table_columns(dbconn, tablename):
    """
    Return a list of tuples specifying the column name and type
    :return:
    """
    cur = dbconn.cursor()
    cur.execute("PRAGMA table_info(%s);" % tablename)
    info = cur.fetchall()
    cols = [(i[1], i[2]) for i in info]
    return cols


def check_table_exists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = '{}'".format(tablename))
    result = dbcur.fetchone()
    dbcur.close()
    return result[0] == 1


def login_ftp(host, user, passwd, path='', acct='', port=21, timeout=5):
    """
    Create and return a logged in FTP object.
    :return:
    """
    ftp = ftplib.FTP()
    ftp.connect(host=host, port=port, timeout=timeout)
    ftp.login(user=user, passwd=passwd, acct=acct)
    ftp.cwd(path)
    logger.debug('Login to %s successful.' % host)
    return ftp


def get_rows(dbconn, tablename):
    cursor = dbconn.cursor()
    cursor.execute("SELECT * FROM %s" % tablename)
    rows = cursor.fetchall()
    return rows

def merge_databases(master, part):
    master.row_factory = part.row_factory = None
    mcur = master.cursor()
    pcur = part.cursor()

    logger.debug("Merging databases...")
    tables = get_table_list(part)
    for table in tables:
        cols = get_table_columns(part, table)
        pcur.execute("SELECT * FROM %s" % table)
        rows = pcur.fetchall()
        if rows:
            logger.debug("Found   {n} rows of table {name} in master".format(name=table, n=rows[-1][1]))
            if not check_table_exists(master, table):
                create_table(master, table, cols)

            args = ("?," * len(cols))[:-1]
            query = 'INSERT INTO {name} VALUES ({args})'.format(name=table, args=args)
            mcur.executemany(query, rows)
            logger.debug("Merging {m} rows of table {name} into master".format(name=table, m=len(rows)))

    master.row_factory = part.row_factory = sqlite3.Row
    master.commit()

