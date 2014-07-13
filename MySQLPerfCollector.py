# Collectd collector that monitors relevant MySQL performance_schema values
# For now only monitors replication load
#
# Original version (c) 2012 Dennis Kaarsemaker <dennis@kaarsemaker.net>
# collectd porting - (c) 2014 Denis Zhdanov <denis.zhdanov@gmail.com>
#
from __future__ import division

try:
    import MySQLdb
    from MySQLdb import MySQLError
except ImportError:
    MySQLdb = None

class MySQLPerfCollector(object):

    def __init__(self, verbose_logging=False):
        self.plugin_name = 'MySQLPerfCollector'
        self.plugin_instance = 'ps'
        self.collectd_type = 'gauge'
        self.verbose_logging = verbose_logging
        self.host = 'localhost'
        self.port = 3306
        self.user = 'root'
        self.password = ''
        self.db_name = 'performance_schema'

        self.db = None
        self.cursor = None
        self.last_wait_count = {}
        self.last_wait_sum = {}
        self.last_timestamp = {}
        self.last_data = {}
        self.monitors = {
            'slave_sql': {
                'wait/synch/cond/sql/MYSQL_RELAY_LOG::update_cond': 'wait_for_update',
                'wait/io/file/innodb/innodb_data_file':             'innodb_data_file',
                'wait/io/file/innodb/innodb_log_file':              'innodb_log_file',
                'wait/io/file/myisam/dfile':                        'myisam_dfile',
                'wait/io/file/myisam/kfile':                        'myisam_kfile',
                'wait/io/file/sql/binlog':                          'binlog',
                'wait/io/file/sql/relay_log_info':                  'relaylog_info',
                'wait/io/file/sql/relaylog':                        'relaylog',
                'wait/synch/mutex/innodb':                          'innodb_mutex',
                'wait/synch/mutex':                                 'other_mutex',
                'wait/synch/rwlock':                                'rwlocks',
                'wait/io':                                          'other_io',
            },
            'slave_io': {
                'wait/io/file/sql/relaylog_index':                  'relaylog_index',
                'wait/synch/mutex/sql/MYSQL_RELAY_LOG::LOCK_index': 'relaylog_index_lock',
                'wait/synch/mutex/sql/Master_info::data_lock':      'master_info_lock',
                'wait/synch/mutex/mysys/IO_CACHE::append_buffer_lock': 'append_buffer_lock',
                'wait/synch/mutex/sql/LOG::LOCK_log':               'log_lock',
                'wait/io/file/sql/master_info':                     'master_info',
                'wait/io/file/sql/relaylog':                        'relaylog',
                'wait/synch/mutex':                                 'other_mutex',
                'wait/synch/rwlock':                                'rwlocks',
                'wait/io':                                          'other_io',
            }
        }

    def connect(self):
        if MySQLdb is None:
            collectd.error('Unable to import MySQLdb')
            return

        params = {}
        params['host'] = self.host
        params['port'] = self.port
        params['db'] = self.db_name
        params['user'] = self.user
        params['passwd'] = self.password

        try:
            self.db = MySQLdb.connect(**params)
        except MySQLError, e:
            self.log_verbose('MySQLPerfCollector couldn\'t connect to database %s' % e, 'error')
            return {}

        self.log_verbose('MySQLPerfCollector: Connected to database.')

    def slave_load(self, thread):
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT
                his.event_name,
                his.sum_timer_wait,
                his.count_star,
                cur.event_name,
                UNIX_TIMESTAMP(SYSDATE())
            FROM
                events_waits_summary_by_thread_by_event_name his
                JOIN threads thr USING (thread_id)
                JOIN events_waits_current cur USING (thread_id)
            WHERE
                name = %s
            ORDER BY
                his.event_name
            """, (thread,))

        data = list(cursor.fetchall())
        if not data:
            self.log_verbose('Got no thread info, master server?')
            return

        wait_sum = sum([x[1] for x in data])
        wait_count = sum([x[2] for x in data])
        cur_event_name, timestamp = data[0][3:]
        self.cursor = cursor

        if thread not in self.last_wait_sum:
            # Avoid bogus data
            self.last_wait_sum[thread], self.last_wait_count[thread], self.last_timestamp[thread] = \
                wait_sum, wait_count, timestamp
            self.last_data[thread] = data
            return

        wait_delta = wait_sum - self.last_wait_sum[thread]
        time_delta = (timestamp - self.last_timestamp[thread]) * 1000000000000

        # Summarize a few things
        thread_name = thread[thread.rfind('/')+1:]
        data.append(['wait/synch/mutex/innodb', sum([x[1] for x in data if x[0].startswith('wait/synch/mutex/innodb')])])
        data.append(['wait/synch/mutex', sum([x[1] for x in data if x[0].startswith('wait/synch/mutex')
                                              and x[0] not in self.monitors[thread_name]]) - data[-1][1]])
        data.append(['wait/synch/rwlock', sum([x[1] for x in data if x[0].startswith('wait/synch/rwlock')])])
        data.append(['wait/io', sum([x[1] for x in data if x[0].startswith('wait/io')
                                     and x[0] not in self.monitors[thread_name]])])

        for d in zip(self.last_data[thread], data):
            if d[0][0] in self.monitors[thread_name]:
                self.dispatch_value(thread_name + '.' + self.monitors[thread_name][d[0][0]],
                                    int((d[1][1] - d[0][1])/time_delta * 100))

        # Also log what's unaccounted for. This is where Actual Work gets done
        self.dispatch_value(thread_name + '.other_work',  int(float(time_delta - wait_delta) / time_delta * 100))

        self.last_wait_sum[thread], self.last_wait_count[thread], self.last_timestamp[thread] = \
            wait_sum, wait_count, timestamp
        self.last_data[thread] = data

    def log_verbose(self, msg, level='info'):
        if not self.verbose_logging:
            return
        elif __name__ == '__main__':
            print msg
        elif level == 'error':
            collectd.error('%s plugin [verbose]: %s' % (self.plugin_name, msg))
        elif level == 'warning':
            collectd.warning('%s plugin [verbose]: %s' % (self.plugin_name, msg))
        else:
            collectd.info('%s plugin [verbose]: %s' % (self.plugin_name, msg))

    def dispatch_value(self, instance, value):
        """Dispatch a value to collectd"""
        self.log_verbose('Sending value: %s.%s.%s=%s' % (self.plugin_name, self.plugin_instance, instance, value))
        if value < 0:
            self.log_verbose('Value %s=%s is negative, skipping' % (instance, value))
            return
        if __name__ == "__main__":
            return
        val = collectd.Values()
        val.plugin = self.plugin_name
        val.plugin_instance = self.plugin_instance
        val.type = self.collectd_type
        val.type_instance = instance
        val.values = [value, ]
        val.dispatch()

    def read_callback(self):
        try:
            self.slave_load('thread/sql/slave_io')
            self.slave_load('thread/sql/slave_sql')
        except MySQLdb.OperationalError:
            self.connect()
            self.slave_load('thread/sql/slave_io')
            self.slave_load('thread/sql/slave_sql')

    def configure_callback(self, conf):
        """Receive configuration block"""
        for node in conf.children:
            if node.key == 'Host':
                self.host = node.values[0]
            elif node.key == 'Port':
                self.port = int(node.values[0])
            elif node.key == 'DB':
                self.db = node.values[0]
            elif node.key == 'User':
                self.user = node.values[0]
            elif node.key == 'Password':
                self.password = node.values[0]
            elif node.key == 'Verbose':
                self.verbose_logging = bool(node.values[0])
            elif node.key == 'InstanceName':
                self.plugin_instance = node.values[0]
            elif node.key == 'NamePrefix':
                self.plugin_name = node.values[0] + self.plugin_name
            else:
                self.log_verbose('%s plugin: Unknown config key: %s.' % (self.plugin_name, node.key), 'warning')
        self.log_verbose('Configured with host=%s,port=%s,db=%s' % (self.host, self.port, self.db))
        self.connect()
        self.log_verbose('Successfully connected to host=%s,port=%s,db=%s' % (self.host, self.port, self.db))


if __name__ == "__main__":
    import time
    conn = MySQLPerfCollector(verbose_logging=True)
    conn.connect()
    conn.log_verbose('First run')
    conn.read_callback()
    conn.log_verbose('Sleeping 5 sec')
    time.sleep(5)
    conn.log_verbose('Second run')
    conn.read_callback()
    conn.log_verbose('End')
else:
    import collectd
    conn = MySQLPerfCollector()
    # register callbacks
    collectd.register_config(conn.configure_callback)
    collectd.register_read(conn.read_callback)