AnonymousUsage
==============

Anonymously track user usage patterns and statistics. The goal of this library is to help developers get a broader 
understanding of their applications usage.



Usage
=====

The basic idea of this module is to anonymously track a users behaviour and upload them to the developer.
AnonymousUsage works by creating a database that contains the statistics you want to track. These statistics
can be either a number, state or time interval. These generally encompass all the different data types one 
would want to track. 

User information is added to the database with a unique identifier or UUID. This should be a unique string code that
can distinguish users from one another. Check out the [uuid](https://docs.python.org/2/library/uuid.html) module for
help on creating unique identifiers.



Example
=======
For example, say we are creating a RPG game. The user creates a character, fights different monsters, completes quests
and levels up. There are a number of different statistics we can track for a particular user. In our example we will track
the name of the server they join, the number of quests completed, the number of monsters killed and the total time they
spent playing the game.


Creating the Tracker
--------------------
We start by creating a AnonymousUsageTracker instance with a UUID for the user. We can use the
uuid module to create a unique identifier for the user. The usage tracker accepts a configuration file which can
store the login credentials for the FTP server. The tracker spawns a thread that will check every `check_interval` to 
see if the `submit_interval` has passed and then uploads the database if it has. Only partial databases are uploaded,
meaning that only the stats that have been added since the last upload are added to the FTP server. The developer will
need to periodically merge and consolidate the partial databases on the FTP site (see the DataManager class in analysis.py)


```python
    import uuid
    import datetime
    from anonymoususage import AnonymousUsageTracker
    
    unique_identifier = uuid.uuid4() 
    database_path = 'data/usage.db'
    submit_interval = datetime.timedelta(hours=1)

    tracker = AnonymousUsageTracker(uuid=unique_identifier,
                                    tracker_file=database_path,
                                    config='./anonymoususage.cfg',
                                    check_interval=datetime.timedelta(seconds=30),
                                    submit_interval=submit_interval)

```

anonymoususage.cfg

```
    [FTP]
    host = ftp.my_rpg.com
    user = my_rpg
    passwd = th394h2GDF
    path = ./usage

```

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
        # Completing quest code goes here
        tracker['monsters_killed'] += 1

```

