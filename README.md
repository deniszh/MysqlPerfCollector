MySQLPerfCollector
=============================

This is a MySQL performance_schema monitor to be used by [collectd] (http://collectd.org) to collect data for
[Graphite] (http://graphite.readthedocs.org).

At the moment it only collects replication load information, giving you insight
in how loaded your single-threaded mysql replication is.
Please see this [post] (http://www.kaarsemaker.net/blog/2012/09/27/monitoring-replication-load-graphite/) for details.

Original [Diamond] (https://github.com/BrightcoveOS/Diamond/) plugin (c) 2012, Dennis Kaarsemaker <dennis@kaarsemaker.net>
Port to [Collectd] (http://collectd.org) (c) 2014, Denis Zhdanov <denis.zhdanov@gmail.com>

Requirements
--------------
Python 2.6, python-mysqldb, collectd, MySQL 5.6 (do not test on 5.5)

Install
-------
 0. Enable PERFORMACE_SCHEMA and 'events_waits_current' consumer
 See [documentation] (https://dev.mysql.com/doc/refman/5.6/en/performance-schema-quick-start.html) 
 1. Place MySQLPerfCollector.py in /usr/lib/collectd/plugins/python.
 2. Configure the plugin (see below).
 3. Restart collectd.

Configuration
-------------
Add the following to your collectd config

    <LoadPlugin python>
      Globals true
    </LoadPlugin>
    
    <Plugin python>
      ModulePath "/usr/lib/collectd/plugins/python"
      Import "MySQLPerfCollector"
    
      <Module MySQLPerfCollector>
        Host "localhost"
        User "collectd"
        Password "SomePass"
        InstanceName "ps"
      </Module>
    </Plugin>