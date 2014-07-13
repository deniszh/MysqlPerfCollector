This is a MySQL performance_schema monitor to be used by [collectd] (http://collectd.org) to collect data for
[Graphite] (http://graphite.readthedocs.org).

At the moment it only collects replication load information, giving you insight
in how loaded your single-threaded mysql replication is.
Please see this [post] (http://www.markleith.co.uk/2012/07/24/a-mysql-replication-load-average-with-performance-schema/) for details.

Original Diamond (https://github.com/BrightcoveOS/Diamond/) plugin (c) 2012, Dennis Kaarsemaker <dennis@kaarsemaker.net>
Port to [Collectd] (http://collectd.org) (c) 2014, Denis Zhdanov <denis.zhdanov@gmail.com>