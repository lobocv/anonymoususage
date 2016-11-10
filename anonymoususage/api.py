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

    CMD_GET = ('total_seconds', 'total_minutes', 'total_hours', 'total_days')
    CMD_PUT = ('start_timer', 'pause_timer', 'resume_timer', 'stop_timer')
    RESPONSES_PUT = {'start_timer': 'Timer trackable "{name}" has been started',
                      'pause_timer': 'Timer trackable "{name}" has been paused',
                      'resume_timer': 'Timer trackable "{name}" has been resumed',
                      'stop_timer': 'Timer trackable "{name}" has been stopped. Timer was running for {dt:.1f} seconds',
                     }
    @cherrypy.tools.json_out()
    def GET(self, name=None, attribute='total_seconds'):
        if name is None:
            return {s.name: {attr: getattr(s, attr) for attr in self.CMD_GET} for s in self.tracker.states}
        else:
            trackable = self.tracker[name]
            if trackable:
                if attribute in self.CMD_GET:
                    return {attribute: getattr(trackable, attribute)}
            else:
                raise cherrypy.HTTPError(404, 'No timer trackable by the name of %s' % name)

    def PUT(self, name, action, *args):
        if self.tracker[name]:
            if action in self.CMD_PUT:
                dt = getattr(self.tracker[name], action)()
                return self.RESPONSES_PUT[action].format(name=name, dt=dt)
            else:
                raise cherrypy.HTTPError(404, 'Invalid command on timer. Use one of start_timer, stop_timer,'
                                              'pause_timer, resume_timer ')
        else:
            raise cherrypy.HTTPError(404, 'No timer trackable by the name of %s' % name)

    def POST(self, name, description='', max_rows=None, **kwargs):
        try:
            self.tracker.track_time(name, str(description), max_rows, **kwargs)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'Timer by the name of "%s" already exists' % name)
        else:
            return 'Timer by the name of "%s" has been created' % name


class SequenceView(TrackableView):
    CMD_GET       = {'count', 'sequence', 'checkpoint', 'checkpoints'}
    CMDS_PUT      = {'set', 'get_checkpoints', 'remove_checkpoint', 'clear_checkpoints', 'advance_to_checkpoint'}
    RESPONSES_PUT = {'set':                   'Sequence trackable "{name}" checkpoint set to "{cp}"',
                     'remove_checkpoint':     'Timer trackable "{name}"\'s last checkpoint {cp} has been removed',
                     'advance_to_checkpoint': 'Sequence trackable "{name}" has been advanced to checkpoint {cp}',
                     'clear_checkpoints':     'All checkpoints for sequence trackable "{name}" have been cleared.'
                     }

    @ cherrypy.tools.json_out()
    def GET(self, name=None, attribute=None):
        if name is None:
            return {s.name: {attr: getattr(s, attr) for attr in self.CMD_GET} for s in self.tracker.states}
        else:
            trackable = self.tracker[name]
            if trackable:
                if attribute in self.CMD_GET:
                    return {attribute: getattr(trackable, attribute)}
                elif attribute is None:
                    return {attr: getattr(trackable, attr) for attr in self.CMD_GET}
                else:
                    raise cherrypy.HTTPError(404, 'No attribute by the name of %s' % attribute)
            else:
                raise cherrypy.HTTPError(404, 'No sequence trackable by the name of %s' % name)

    def PUT(self, name, action, *args):
        if self.tracker[name]:
            if action in self.CMDS_PUT:
                if action == 'set':
                    cp = str(args[0])
                    try:
                        self.tracker[name] = cp
                    except InvalidCheckpointError:
                        raise cherrypy.HTTPError(404, 'Assigned checkpoint is not in the defined list of '
                                                      'checkpoints: %s' % ', '.join(self.tracker[name].checkpoints))
                else:
                    cp = getattr(self.tracker[name], action)(*args)
                return self.RESPONSES_PUT[action].format(name=name, cp=cp)
            else:
                raise cherrypy.HTTPError(404, 'Invalid command on sequence. Use one of %s' % ', '.join(self.CMDS_PUT))
        else:
            raise cherrypy.HTTPError(404, 'No sequence trackable by the name of %s' % name)

    def POST(self, name, checkpoints, description='', max_rows=None):
        try:
            cp = checkpoints.split(',')
        except Exception as e:
            raise cherrypy.HTTPError(400, 'Checkpoints arguments must be comma separated with no spaces. '
                                          'Example: a,b,c,d')
        try:
            self.tracker.track_sequence(name, cp, str(description), max_rows)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'Sequence by the name of "%s" already exists' % name)
        else:
            return 'Sequence by the name of "%s" has been created' % name


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