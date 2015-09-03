import uuid
import datetime
from anonymoususage import AnonymousUsageTracker, NO_STATE

unique_identifier = uuid.uuid4().hex
database_path = 'data/usage.db'
submit_interval = datetime.timedelta(hours=1)

tracker = AnonymousUsageTracker(uuid=unique_identifier,
                                tracker_file=database_path,
                                config='./anonymoususage.cfg',
                                check_interval=datetime.timedelta(seconds=30),
                                submit_interval=submit_interval)

tracker.track_statistic('quests_complete')
tracker.track_statistic('monsters_killed')
tracker.track_state('server', initial_state=NO_STATE)
tracker.track_time('play_time')


def login(server_name, username, password):
    # Login code goes here

    # Start the play_time timer.
    tracker['play_time'].start_timer()
    tracker['server'] = server_name


def logoff():
    # Logoff code goes here

    # Stop the timer
    tracker['play_time'].stop_timer()

def hand_in_quests(quests):
    # Completing quest code goes here
    tracker['quests_complete'] += len(quests)


def kill_monster():
    # Completing quest code goes here
    tracker['monsters_killed'] += 1


sdf=3
tracker.close()

