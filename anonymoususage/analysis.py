__author__ = 'calvin'

import logging

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from tools import *


def plot_stat(dbconn, table_names, uuid=None, date_limits=(None, None), datefmt=None):

    max_cols = 3
    nrows = max(1, len(table_names) / max_cols)
    ncols = len(table_names) % max_cols
    fig, plots = plt.subplots(nrows=nrows, ncols=ncols)
    if len(table_names) == 1:
        plots = [plots]
    if uuid:
        plt.title(uuid)

    plotted_tables = set()
    if uuid is None:
        uuids = get_uuid_list(dbconn)
    else:
        uuids = [uuid]
    for uuid in uuids:
        for ii, table_name in enumerate(table_names):

            plot = plots[ii]
            if datefmt:
                plot.xaxis.set_major_formatter(DateFormatter(datefmt))
            plot.set_xlabel('Date')
            plot.set_ylabel('Count')

            data = get_datetime_sorted_rows(dbconn, table_name, uuid=uuid, column='Count')
            if data:
                times, counts = zip(*data)
                plot.plot_date(times, counts, '-o', label=table_name)
                plotted_tables.add(table_name)
            else:
                logging.warning('No data for %s. Omitting from plot.' % table_name)

        if len(plotted_tables) == 0:
            logging.warning('No data for found. Failed to create plot.')
            return

    legend_fields = plt.legend(plotted_tables, loc='center left', bbox_to_anchor=(0, 1),
                               fancybox=True, ncol=max(1, 3 * (len(plotted_tables) / 3)))

    legend_uuids = plt.legend(uuids, loc='center right', bbox_to_anchor=(1, 1), title='UUID',
                              fancybox=True, ncol=max(1, 3 * (len(plotted_tables) / 3)))
    plt.gca().add_artist(legend_fields)

    if date_limits[0] and date_limits[1]:
        plots.set_xlim(*date_limits)
    else:
        fig.autofmt_xdate()
    fig.set_size_inches(12, 8, forward=True)
    plt.show()

