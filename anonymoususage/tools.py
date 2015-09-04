__author__ = 'calvin'

import ftplib
import sqlite3
import logging
import datetime


logger = logging.getLogger('AnonymousUsage')

__all__ = ['create_table', 'get_table_list', 'get_table_columns', 'check_table_exists', 'login_ftp', 'get_rows',
           'merge_databases', 'ftp_download', 'get_datetime_sorted_rows', 'delete_row', 'get_uuid_list',
           'get_number_of_rows', 'get_last_row']


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


def delete_row(dbconn, table_name, field, value):
    """
    Delete a row from a table in a database.
    :param dbconn: data base connection
    :param table_name: name of the table
    :param field: field of the table to target
    :param value: value of the field in the table to delete
    """
    cur = dbconn.cursor()
    cur.execute("DELETE FROM {name} WHERE {field}={value}".format(name=table_name, field=field, value=value))


def get_table_list(dbconn):
    """
    Get a list of tables that exist in dbconn
    :param dbconn: database connection
    :return: List of table names
    """
    cur = dbconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [item[0] for item in cur.fetchall()]


def get_uuid_list(dbconn):
    """
    Get a list of tables that exist in dbconn
    :param dbconn: master database connection
    :return: List of uuids in the database
    """
    cur = dbconn.cursor()
    tables = get_table_list(dbconn)
    uuids = set()
    for table in tables:
        cur.execute("SELECT (UUID) FROM {table}".format(table=table))
        uuid = set([i[0] for i in cur.fetchall()])
        if uuid:
            uuids.update(uuid)
    return uuids


def get_table_columns(dbconn, tablename):
    """
    Return a list of tuples specifying the column name and type
    """
    cur = dbconn.cursor()
    cur.execute("PRAGMA table_info(%s);" % tablename)
    info = cur.fetchall()
    cols = [(i[1], i[2]) for i in info]
    return cols


def get_number_of_rows(dbcon, tablename, uuid=None):
    """
    Return the number of rows in a table
    :param dbcon: database connection
    :param tablename: table name
    :return: Boolean
    """
    dbcur = dbcon.cursor()
    if check_table_exists(dbcon, tablename):
        if uuid:
            dbcur.execute("SELECT COUNT(*) FROM {name} WHERE UUID='{uuid}'".format(name=tablename, uuid=uuid))
        else:
            dbcur.execute("SELECT COUNT(*) FROM {name}".format(name=tablename))
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


def get_rows(dbconn, tablename, uuid=None):
    """
    Return all the rows in a table from dbconn
    :param dbconn: database connection
    :param tablename: name of the table
    :return: List of sqlite3.Row objects
    """
    cursor = dbconn.cursor()
    if uuid:
        cursor.execute("SELECT * FROM  {tablename} WHERE UUID='{uuid}'".format(tablename=tablename, uuid=uuid))
    else:
        cursor.execute("SELECT * FROM %s" % tablename)
    rows = cursor.fetchall()
    return rows


def get_last_row(dbconn, tablename, n=1, uuid=None):
    """
    Returns the last `n` rows in the table
    :param dbconn: database connection
    :param tablename: name of the table
    :param n: number of rows to return from the end of the table
    :param uuid: Optional UUID to select from
    :return: If n > 1, a list of rows. If n=1, a single row
    """
    cur = dbconn.cursor()
    if uuid:
        cur.execute("SELECT * FROM {} WHERE UUID='{}' ORDER BY Count DESC LIMIT {};".format(tablename, uuid, n))
    else:
        cur.execute("SELECT * FROM {} ORDER BY Count DESC LIMIT {};".format(tablename, n))
    rows = cur.fetchall()
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


def ftp_download(ftp, ftp_path, local_path):
    """
    Download the master database
    :param ftp: ftp connection
    :param ftp_path: path to file on the ftp server
    :param local_path: local path to download file
    :return:
    """
    with open(local_path, 'wb') as _f:
        ftp.retrbinary('RETR %s' % ftp_path, _f.write)


def get_datetime_sorted_rows(dbconn, table_name, uuid=None, column=None):
    rows = get_rows(dbconn, table_name, uuid=uuid)
    data = []
    for r in rows:
        dt = datetime.datetime.strptime(r['Time'], "%d/%m/%Y %H:%M:%S")
        if column is None:
            data.append((dt, r))
        else:
            data.append((dt, r[column]))
    data.sort()

    return data
