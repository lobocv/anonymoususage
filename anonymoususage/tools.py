from reportlab.graphics.widgets import table

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
    """
    Get a list of tables that exist in dbconn
    :param dbconn: database connection
    :return: List of table names
    """
    cur = dbconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [item[0] for item in cur.fetchall()]


def get_table_columns(dbconn, tablename):
    """
    Return a list of tuples specifying the column name and type
    """
    cur = dbconn.cursor()
    cur.execute("PRAGMA table_info(%s);" % tablename)
    info = cur.fetchall()
    cols = [(i[1], i[2]) for i in info]
    return cols


def get_number_of_rows(dbcon, tablename):
    """
    Return the number of rows in a table
    :param dbcon: database connection
    :param tablename: table name
    :return: Boolean
    """
    dbcur = dbcon.cursor()
    if check_table_exists(dbcon, tablename):
        dbcur.execute("SELECT COUNT(*) FROM {}".format(tablename))
        result = dbcur.fetchone()
        dbcur.close()
        return result[0]
    else:
        return 0


def check_table_exists(dbcon, tablename):
    """
    Check if a table exists in the database.
    :param dbcon: database connection
    :param tablename: table name
    :return: Boolean
    """
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s';" % tablename)
    result = dbcur.fetchone()
    dbcur.close()
    if result is None:
        return False
    else:
        return result[0] == tablename


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
    """
    Return all the rows in a table from dbconn
    :param dbconn: database connection
    :param tablename: name of the table
    :return: List of sqlite3.Row objects
    """
    cursor = dbconn.cursor()
    cursor.execute("SELECT * FROM %s" % tablename)
    rows = cursor.fetchall()
    return rows


def merge_databases(master, part):
    """
    Merge the partial database into the master database.
    :param master: database connection to the master database
    :param part: database connection to the partial database
    """
    mcur = master.cursor()
    pcur = part.cursor()

    logger.debug("Merging databases...")
    tables = get_table_list(part)
    for table in tables:
        cols = get_table_columns(part, table)
        pcur.execute("SELECT * FROM %s" % table)
        rows = pcur.fetchall()
        if rows:
            logger.debug("Found   {n} rows of table {name} in master".format(name=table, n=rows[0][1]-1))
            if not check_table_exists(master, table):
                create_table(master, table, cols)

            args = ("?," * len(cols))[:-1]
            query = 'INSERT INTO {name} VALUES ({args})'.format(name=table, args=args)
            mcur.executemany(query, tuple(tuple(r) for r in rows))
            logger.debug("Merging {m} rows of table {name} into master".format(name=table, m=len(rows)))

    master.commit()

