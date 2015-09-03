__author__ = 'calvin'

import logging
import itertools
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from tools import *


def _get_figure(n_items):
    figure, plots = plt.subplots(nrows=n_items, ncols=1, sharex=True)
    if n_items == 1:
        plots = [plots]
    else:
        plots = plots.flatten()
    return figure, plots[:n_items]


def plot_statistic(dbconn, table_names, uuid=None, date_limits=(None, None), datefmt=None):
    fig, plots = _get_figure(len(table_names))

    plotted_tables = set()
    handles = []
    uuids = get_uuid_list(dbconn) if uuid is None else [uuid]
    colors = [c for c in itertools.islice(plots[0]._get_lines.color_cycle, 0, len(uuids))]

    for ii, table_name in enumerate(table_names):
        for jj, uuid in enumerate(uuids):
            data = get_datetime_sorted_rows(dbconn, table_name, uuid=uuid, column='Count')
            if len(data) > 1:
                plot = plots.flatten()[ii]
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

