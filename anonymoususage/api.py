import cherrypy
from exceptions import *
from anonymoususage import AnonymousUsageTracker


class TrackableView():
    exposed = True
    tracker = None


class StatisticView(TrackableView):

    @cherrypy.tools.json_out()
    def GET(self, name=None):
        if name is None:
            return {s.name: s.count for s in self.tracker.statistics}
        else:
            trackable = self.tracker[name]
            if trackable:
                return {'count': trackable.count}
            else:
                raise cherrypy.HTTPError(404, 'No statistic trackable by the name of %s' % name)

    def PUT(self, name, action, *args):
        if self.tracker[name]:
            if action == 'set':
                self.tracker[name] = float(args[0])
            elif action == 'increment':
                self.tracker[name] += 1 if len(args) == 0 else float(args[0])
            elif action == 'decrement':
                self.tracker[name] -= 1 if len(args) == 0 else float(args[0])
            return 'Statistic trackable "%s" set to %g' % (name, self.tracker[name].count)
        else:
            raise cherrypy.HTTPError(404, 'No state trackable by the name of %s' % name)

    def POST(self, name, description='', max_rows=None):
        try:
            self.tracker.track_statistic(name, str(description), max_rows)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'Statistic by the name of "%s" already exists' % name)
        else:
            return 'Statistic by the name of "%s" has been created' % name


class StateView(TrackableView):

    @cherrypy.tools.json_out()
    def GET(self, name=None):
        if name is None:
            return {s.name: {'count': s.count, 'state': s.state} for s in self.tracker.states}
        else:
            trackable = self.tracker[name]
            if trackable:
                return {'state': trackable.state, 'count': trackable.count}
            else:
                raise cherrypy.HTTPError(404, 'No state trackable by the name of %s' % name)

    def PUT(self, name, action, *args):
        if self.tracker[name]:
            if action == 'set':
                self.tracker[name] = None if args[0].lower() == 'none' else args[0]
            return 'State trackable "%s" set to %s' % (name, self.tracker[name].state)
        else:
            raise cherrypy.HTTPError(404, 'No state trackable by the name of %s' % name)

    def POST(self, name, value, description='', max_rows=None, **kwargs):
        try:
            self.tracker.track_state(name, str(value), str(description), max_rows, **kwargs)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'State by the name of "%s" already exists' % name)
        else:
            return 'State by the name of "%s" has been created' % name


class TimerView(TrackableView):
    pass


class SequenceView(TrackableView):
    pass


class UsageTrackerServer(AnonymousUsageTracker):

    def __init__(self, *args, **kwargs):
        super(UsageTrackerServer, self).__init__(*args, **kwargs)
        TrackableView.tracker = self

    @cherrypy.expose
    def index(self):
        return 'Nothing to see here'

    def run(self):
        cherrypy.tree.mount(self, '/')

        cherrypy.tree.mount(StatisticView(),
                            '/statistics',
                            {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})

        cherrypy.tree.mount(StateView(),
                            '/states',
                            {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})

        cherrypy.tree.mount(TimerView(),
                            '/timers',
                            {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})

        cherrypy.tree.mount(SequenceView(),
                            '/sequences',
                            {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})

        cherrypy.engine.start()
        cherrypy.engine.block()