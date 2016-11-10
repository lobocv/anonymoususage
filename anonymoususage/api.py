import cherrypy
from exceptions import *
from anonymoususage import AnonymousUsageTracker


class TrackableView(object):
    exposed = True
    tracker = None

    def __init__(self):
        self.trackable_class = self.__class__.__name__.replace('View', '')

    def decode_PUT_input(self, action, *string_inputs):
        """
        With this function you can interpret the string input sent to the PUT() function so that it can
        be passed to the underlying PUT functions.
        :param action: PUT action
        :param string_inputs: request arguments (*args)
        :return: interpreted arguments that get passed to PUT as *args (doesn't have to be strings)
        """
        return string_inputs

    @property
    def all_trackables(self):
        attr = self.trackable_class.lower() + 's'
        return getattr(self.tracker, attr)

    def PUT(self, name, action, *args):
        _args = self.decode_PUT_input(action, *args)
        if self.tracker[name]:
            if action in self.CMD_PUT:
                result = getattr(self.tracker[name], action)(*_args)
                return self.RESPONSES_PUT[action].format(result, name=name)
            else:
                raise cherrypy.HTTPError(404, 'Invalid command on {cls}. Use one of '
                                              '{responses}'.format(cls=self.trackable_class,
                                                                   responses=', '.join(self.RESPONSES_PUT.keys())))

        else:
            raise cherrypy.HTTPError(404, 'No {cls} trackable by the name of'
                                          ' {name}'.format(cls=self.trackable_class.lower(), name=name))

    @cherrypy.tools.json_out()
    def GET(self, name=None, attribute=None):
        if name is None:
            return {s.name: {attr: getattr(s, attr) for attr in self.CMD_GET} for s in self.all_trackables}
        else:
            trackable = self.tracker[name]
            if trackable:
                if attribute in self.CMD_GET:
                    return {attribute: getattr(trackable, attribute)}
                elif attribute is None:
                    return {attr: getattr(trackable, attr) for attr in self.CMD_GET}
            else:
                raise cherrypy.HTTPError(404, 'No {cls} trackable by the name of'
                                              ' {name}'.format(cls=self.trackable_class.lower(), name=name))


class StatisticView(TrackableView):
    CMD_GET = ('count', )
    CMD_PUT = ('set', 'increment', 'decrement')
    RESPONSES_PUT = {'set'      : 'Statistic trackable {name} count set to {}',
                     'increment': 'Statistic trackable {name} count incremented to {}',
                     'decrement': 'Statistic trackable {name} count decremented to {}'}

    def POST(self, name, description='', max_rows=None):
        try:
            self.tracker.track_statistic(name, str(description), max_rows)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'Statistic by the name of "%s" already exists' % name)
        else:
            return 'Statistic by the name of "%s" has been created' % name


class StateView(TrackableView):
    CMD_GET = ('state', 'count')
    CMD_PUT = ('set', )
    RESPONSES_PUT = {'set': 'State trackable "{name}" set to {}'}

    def decode_PUT_input(self, action, *string_inputs):
        if action == 'set':
            # Convert string 'none' into None value
            value = string_inputs[0]
            if isinstance(value, basestring):
                state = None if value.lower() == 'none' else value
            else:
                state = value
            return (state, )
        else:
            return super(StateView, self).decode_PUT_input(action, *string_inputs)

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
    RESPONSES_PUT = {'start_timer' : 'Timer trackable "{name}" has been started',
                     'pause_timer' : 'Timer trackable "{name}" has been paused',
                     'resume_timer': 'Timer trackable "{name}" has been resumed',
                     'stop_timer'  : 'Timer trackable "{name}" has been stopped. Timer was '
                                     'running for {:.1f} seconds'
                     }

    def POST(self, name, description='', max_rows=None, **kwargs):
        try:
            self.tracker.track_time(name, str(description), max_rows, **kwargs)
        except TableConflictError:
            raise cherrypy.HTTPError(400, 'Timer by the name of "%s" already exists' % name)
        else:
            return 'Timer by the name of "%s" has been created' % name


class SequenceView(TrackableView):
    CMD_GET       = {'count', 'sequence', 'checkpoint', 'checkpoints'}
    CMD_PUT      = {'set', 'get_checkpoints', 'remove_checkpoint', 'clear_checkpoints', 'advance_to_checkpoint'}
    RESPONSES_PUT = {'set'                  : 'Sequence trackable "{name}" checkpoint set to "{}"',
                     'remove_checkpoint'    : 'Timer trackable "{name}"\'s last checkpoint {} has been removed',
                     'advance_to_checkpoint': 'Sequence trackable "{name}" has been advanced to checkpoint {}',
                     'clear_checkpoints'    : 'All checkpoints for sequence trackable "{name}" have been cleared.'
                     }

    def PUT(self, name, action, *args):
        try:
            result = super(SequenceView, self).PUT(name, action, *args)
            return result
        except InvalidCheckpointError:
            raise cherrypy.HTTPError(404, 'Assigned checkpoint is not in the defined list of '
                                          'checkpoints: %s' % ', '.join(self.tracker[name].checkpoints))

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