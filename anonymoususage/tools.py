__author__ = 'calvin'

import ftplib
import sqlite3


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


def get_table_columns(dbconn, name):
    cursor = dbconn.execute('select * from %s' % name)

    cur = dbconn.cursor()
    cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT 1;" % name)

    cols = [c[0] for c in cursor.description]
    ctypes = []
    for c in cols:
        cur.execute("SELECT typeof(%s) FROM %s DESC LIMIT 1;" % (c, name))
        ctypes.append(cur.fetchone()[0].upper())

    return zip(cols, ctypes)


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

    return ftp

def merge_databases(master, part):
    master.row_factory = part.row_factory = None
    mcur = master.cursor()
    pcur = part.cursor()

    tables = get_table_list(master)
    for table in tables:
        pcur.execute("SELECT * FROM %s" % table)
        cols = get_table_columns(part)
        rows = pcur.fetchall()
        if rows:
            n = rows[0][1]
            m = n + len(rows) - 1
            if not check_table_exists(master, table):
                create_table(master, table, cols)

            args = ("?," * len(cols))[:-1]
            query = 'INSERT INTO {name} VALUES ({args})'.format(name=table, args=args)
            mcur.executemany(query, rows)

    master.row_factory = part.row_factory = sqlite3.Row
    master.commit()
