AnonymousUsage
==============

Anonymously track user usage patterns and statistics. The goal of this library is to help developers get a broader 
understanding of their applications usage. Each users usage stats are stored locally for them to use and can also
be uploaded to a web app that consolidates and manages all the data (see https://github.com/lobocv/crashreporter_hq).
On crash reporter HQ you can create custom usage plots from all users that have submitted statistics.



Usage
=====

The basic idea of this module is to anonymously track a users behaviour and upload them to the developer.
AnonymousUsage works by creating a database that contains the statistics you want to track. These statistics
can be either a number, state or time interval. These generally encompass all the different data types one 
would want to track. 

User information is added to the database with a unique identifier or UUID. This should be a unique string code that
can distinguish users from one another. Check out the [uuid](https://docs.python.org/2/library/uuid.html) module for
help on creating unique identifiers.

The Tracker Class
=================
To start tracking usage we need to create the usage tracker. We can do this by the class constructor or using 
a configuration file. We need to define a unique identifier for the user (easily done through the uuid module) and the 
location to store the database. If we want the tracker to also upload the stats to the web app we need to specify
the interval for which to do so (submit_interval_s) as well as how often to check if stats need to be uploaded (check_interval_s).
The tracker spawns a thread that will check every `check_interval_s` to see if the `submit_interval_s` has passed.
The tracker will then uploads the database if it has statistics to upload and if the submit interval has passed. 
Only partial databases are uploaded, meaning that only the stats that have been added since the last upload are added to the server.
If you choose to upload your stats to the web server, you must also specify the application name and version.


```python

    import uuid
    import datetime
    from anonymoususage import AnonymousUsageTracker
    
    unique_identifier = uuid.uuid4() 
    database_path = 'data/usage.db'
    submit_interval = datetime.timedelta(hours=1)

    tracker = AnonymousUsageTracker(uuid=unique_identifier,
                                    filepath=database_path,
                                    check_interval_s=5*60),
                                    submit_interval_s=30*60,
                                    application_name='MyApp',
                                    application_version='1.0.0')
                                    
                                    
```

Using a Configuration File
--------------------------
You can also load the tracker from the configuration file

```python

    path = './tracker_config.conf'
    tracker = AnonymousUsageTracker.load_from_configuration(path, uuid, **kwargs)
```

tracker_config.conf
```
    [General]
    filepath = /home/calvin/usage_stats.db
    application_name = MyApp
    application_version = 1.0.0
    submit_interval_s = 500
    check_interval_s = 30000

    [HQ]
    host = www.usagetrackerapp.com
    api_key = ldfhksg23542kj5g73kk3465j
    
```


Trackable Classes
=================

Statistic
---------
Tracks numerical statistics such as counts. Easily set or increment/decrement the value by re 

```python

    tracker.track_statistic('run_number')   # Create the trackable called run_number 
    tracker['run_number'] += 1      # Increment the value
    tracker['run_number'] -= 1      # Decrement the value
    tracker['run_number'] = 1       # Set the value of the trackable
```

State
---------
Track state statistics such as what settings the user is using. The value must be a string. You can initialize
the trackable without a state using the NO_STATE class.
```python
        
        # Create the trackable state called 'Unit System' with default value of 'Metric'
        tracker.track_state('Unit System', 'Metric') 
        tracker['Unit System'] = 'US Standard'  # Set the trackable to 'US Standard'
```

Timer
-----
Track the time in which the user does a particular task. You can get time totals by total_days, total_hours, 
total_minutes, totals_seconds attributes. You can also get the formatted average and total time by calling 
formatted_total_time and formatted_average_time.
```python

        tracker.track_time('task_A')
        
        
        tracker['task_A'].start_timer() # User starts to perform task A
        
        
        tracker['task_A'].pause_timer() # Pause the timer (brb washroom...)
        
        tracker['task_A'].resume_timer() # Ah... much better
        
        # Continue on with Task A....
        
        tracker['task_A'].stop_timer() # User has completed task A
```

Sequence
---------
Track the number of times a user performs a sequence of tasks (hits certain points in the code). The counter only
increments if all the checkpoints are hit in the correct order.
```python

        tracker.track_sequence('my_sequence', ['A', 'B', 'C', 'D'])
        tracker['my_sequence'] = 'A'    # A
        tracker['my_sequence'] = 'B'    # A, B
        tracker['my_sequence'] = 'C'    # A, B, C
        tracker['my_sequence'] = 'D'    # A, B, C, D. We completed the sequence! Counter is updated
        
        tracker['my_sequence'] = 'B'    # B
        tracker['my_sequence'] = 'C'    # B, C
        tracker['my_sequence'].clear_checkpoints() # Resets the checkpoint history
        
        tracker['my_sequence'].advance_to_checkpoint('C') # Advances through A, B and C
        tracker['my_sequence'].get_checkpoints('C') # Returns A, B, C
        tracker['my_sequence'].remove_checkpoint() # Remove the last checkpoint, we're back to A, B
        tracker['my_sequence'] = 'C'    # A, B , C
        tracker['my_sequence'] = 'D'    # A, B, C, D. We completed the sequence! Counter is updated
````

Example
=======
For example, say we are creating a RPG game. The user creates a character, fights different monsters, completes quests
and levels up. There are a number of different statistics we can track for a particular user. In our example we will track
the name of the server they join, the number of quests completed, the number of monsters killed and the total time they
spent playing the game.


Tracking Usage
--------------

Now that the tracker is set up you can now start tracking the statistics as you choose. It is as simple as adding
one line of code to certain functions in your application. Here are some functions that would require tracking code.

```python

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
        # kill monster code goes here
        tracker['monsters_killed'] += 1

```

