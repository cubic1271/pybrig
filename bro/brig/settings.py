__author__ = 'clarkg1'

DEBUG = True
MONGO_DBNAME = 'pybrig'
SERVER_NAME = '127.0.0.1:8100'
# Note: schemas aren't evaluated since we disable validation by passing in a relevant custom validator.
DOMAIN = {
    'systems': {
        'item_title': 'system',
        'schema':
        {
            'cpus': {'type':'list'},
            'interfaces': {'type':'list'},
            'memory': {'type':'integer'},
            'modules': {'type':'list'},
            'partitions': {'type':'list'},
            'pcap_version': {'type':'string'},
            'sysctl': {'type':'dict'},
            'uuid': {'type':'string'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'benchmarks': {
        'item_title': 'benchmark',
        'schema': 
        {
            'uuid': {'type':'string'},
            'system_uuid': {'type':'string'},
            'time': {'type':'float'},
            'trials': {'type':'list'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'sys_profile_entries': {
        'item_title': 'entry',
        'schema': 
        {
            'cmd': {'type':'string'},
            'data': {'type':'list'},
            'start': {'type':'float'},
            'trial_id': {'type':'string'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'call_chains': {
        'item_title': 'entry',
        'schema': 
        {
            'count': {'type':'integer'},
            'trial_id': {'type':'string'},
            'chains': {'type':'dict'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'packet_chains': {
        'item_title': 'entry',
        'schema': 
        {
            'count': {'type':'integer'},
            'trial_id': {'type':'string'},
            'chains': {'type':'dict'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'counts': {
        'item_title': 'entry',
        'schema': 
        {
            'counts': {'type':'integer'},
            'componentCounts': {'type':'dict'},
            'scriptCounts':{'type':'dict'},
            'trial_id':{'type':'string'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'event_paths': {
        'item_title': 'entry',
        'schema': 
        {
            'count': {'type':'integer'},
            'trial_id': {'type':'string'},
            'graph': {'type':'dict'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'mappings': {
        'item_title': 'entry',
        'schema': 
        {
            'trial_id': {'type':'string'},
            'endian': {'type':'string'},
            'components': {'type':'list'},
            'mappings': {'type':'list'},
            'info': {'type':'dict'}
        },
        'resource_methods': ['GET', 'POST']
    },
    'script_timings': {
        'item_title': 'entry',
        'schema': 
        {
            'count': {'type':'integer'},
            'trial_id': {'type':'string'},
            'stats': {'type':'dict'}
        },
        'resource_methods': ['GET', 'POST']
    }
}
ALLOW_UNKNOWN = True
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']
