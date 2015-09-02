__author__ = 'calvin'

import logging

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from tools import *


def plot_stat(dbconn, table_names, date_limits=(None, None)):

    fig, ax = plt.subplots()

    ax.xaxis.set_major_formatter(DateFormatter("%d %B %Y"))
    ax.fmt_xdata = DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    plotted_tables = set()
    for table_name in table_names:
        data = get_datetime_sorted_rows(dbconn, table_name, column='Count')
        if data:
            times, counts = zip(*data)
            ax.plot_date(times, counts, '-', label=table_name)
            plotted_tables.add(table_name)
        else:
            logging.warning('No data for %s. Omitting from plot.' % table_name)
    ax.legend(plotted_tables, loc='center left', bbox_to_anchor=(0, 1),
              fancybox=True, ncol=max(1, 3 * (len(plotted_tables) / 3)))

    if date_limits[0] and date_limits[1]:
        ax.set_xlim(*date_limits)
    else:
        fig.autofmt_xdate()
    fig.set_size_inches(12, 8, forward=True)
    plt.show()

