__author__ = 'calvin'

import logging
import itertools
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter
from collections import Iterable
from tools import *


def _get_figure(n_items):
    figure, plots = plt.subplots(nrows=n_items, ncols=1, sharex=True)
    if n_items == 1:
        return figure, plots
    else:
        plots = plots.flatten()
        return figure, plots[:n_items]


def plot_total_statistics(dbconn, table_names):
    """
    Plot the cumulative statistics for table names in a bar plot.
    :param dbconn: database connection
    :param table_names: list of table names to plot
    """
    fig, plot = _get_figure(1)
    stat_count = {t: 0 for t in table_names}
    uuids = get_uuid_list(dbconn)
    for table in stat_count.iterkeys():
        for uuid in uuids:
            last_row = get_last_row(dbconn, table, uuid=uuid)
            if last_row:
                count = last_row[0]['Count']
                stat_count[table] += count

    table_names, table_values = zip(*stat_count.items())
    ind = np.arange(len(table_names))
    colors = [c for c in itertools.islice(plot._get_lines.color_cycle, 0, len(table_names))]
    plot.bar(ind, table_values, color=colors)
    # add some text for labels, title and axes ticks
    plot.set_ylabel('Count')
    plot.set_title('Statistic Totals')
    plot.set_xticks(ind+0.35)
    plot.set_xticklabels(table_names)
    plt.show()


def plot_statistic(dbconn, table_names, uuid=None, date_limits=(None, None), datefmt=None):
    """
    Plot statistics as a function of time for table names in a line plot.
    :param dbconn: database connection
    :param table_names: list of table names to plot
    :param uuid: UUID to plot, if None all UUIDs will be plotted
    :param data_limits: tuple of (min_datetime, max_datetime) to be used for x axis range
    :param datefmt: string formatter for the date axis

    """
    fig, plots = _get_figure(len(table_names))
    if isinstance(plots, Iterable):
        plots = plots.flatten()
    else:
        plots = [plots]
    plots = list(plots)
    plotted_tables = set()
    handles = []
    uuids = get_uuid_list(dbconn) if uuid is None else [uuid]
    colors = [c for c in itertools.islice(plots[0]._get_lines.color_cycle, 0, len(uuids))]

    for ii, table_name in enumerate(table_names):
        for jj, uuid in enumerate(uuids):
            data = get_datetime_sorted_rows(dbconn, table_name, uuid=uuid, column='Count')
            if len(data) > 1:
                plot = plots[ii]
                plot.set_title(table_name)
                times, counts = zip(*data)
                plot.plot_date(times, counts, '-o%s'% colors[jj], label=table_name)
                plotted_tables.add(table_name)
                if datefmt:
                    plot.xaxis.set_major_formatter(DateFormatter(datefmt))
                plot.set_xlabel('Date')
                plot.set_ylabel('Count')
                _handles = plot.get_legend_handles_labels()[0]
                if len(_handles) > len(handles):
                    handles = _handles
            else:
                logging.warning('No data for %s. Omitting from plot.' % table_name)

        if len(plotted_tables) == 0:
            logging.warning('No data for found. Failed to create plot.')
            return

    # plt.figlegend(handles, plotted_tables, loc='upper left', ncol=max(1, 3 * (len(plotted_tables) / 3)), labelspacing=0.)
    plt.figlegend(handles, uuids, loc='lower left', labelspacing=0.)

    if date_limits[0] and date_limits[1]:
        plots.set_xlim(*date_limits)
    else:
        fig.autofmt_xdate()
    fig.set_size_inches(12, 8, forward=True)
    plt.show()

