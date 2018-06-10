from collections import OrderedDict

from charmhelpers.contrib.openstack import context, templating

from ck_context import *


TEMPLATES = 'templates/'

BASE_PACKAGES = [
    'apache2',
    'libapache2-mod-wsgi',
    'haproxy',
    'rsync',
    'tox',
    'python-pbr',
    'python-oslo.config',
    'python-mysqldb',
    'python-pymysql',
    'build-essential',
    'autoconf',
    'libtool',
    'pkg-config',
    'python-opengl',
    'python-imaging',
    'python-pyrex',
    'python-pyside.qtopengl',
    'idle-python2.7',
    'python-dev',
]

BASE_SERVICES = [
    # 'cloudkitty-api',
    # 'cloudkitty-processor',
]

SVC = 'cloudkitty'
CLOUDKITTY_DIR = '/etc/cloudkitty'
CLOUDKITTY_CONF = '/etc/cloudkitty/cloudkitty.conf'
HAPROXY_CONF = '/etc/haproxy/haproxy.cfg'
HTTPS_APACHE_CONF = ('/etc/apache2/sites-available/'
                     'openstack_https_frontend.conf')

CONFIG_FILES = OrderedDict([
    (CLOUDKITTY_CONF, {
        'services': BASE_SERVICES,
        'contexts': [context.AMQPContext(),
                     context.SharedDBContext(relation_prefix='cloudkitty',
                                             ssl_dir=CLOUDKITTY_DIR),
                     context.OSConfigFlagContext(),
                     context.IdentityServiceContext(service=SVC,
                                                    service_user=SVC),
                     CloudkittyHAProxyContext(),
                     context.SyslogContext()]
    }),
    (HAPROXY_CONF, {
        'contexts': [context.HAProxyContext(singlenode_mode=True),
                     CloudkittyHAProxyContext()],
        'services': ['haproxy'],
    }),
    (HTTPS_APACHE_CONF, {
        'contexts': [CloudkittyApacheSSLContext()],
        'services': ['apache2'],
    })
])


def register_configs():
    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release='mitaka')
    confs = [CLOUDKITTY_CONF, HAPROXY_CONF]
    for conf in confs:
        configs.register(conf, CONFIG_FILES[conf]['contexts'])

    configs.register(HTTPS_APACHE_CONF,
                     CONFIG_FILES[HTTPS_APACHE_CONF]['contexts'])

    return configs


def restart_map():
    """Restarts on config change.

    Determine the correct resource map to be passed to
    charmhelpers.core.restart_on_change() based on the services configured.

    :returns: dict: A dictionary mapping config file to lists of services
    that should be restarted when file changes.
    """
    _map = []
    for f, ctxt in CONFIG_FILES.iteritems():
        svcs = []
        for svc in ctxt['services']:
            svcs.append(svc)
        if svcs:
            _map.append((f, svcs))
    return OrderedDict(_map)


def determine_packages():
    # currently all packages match service names
    packages = BASE_PACKAGES + BASE_SERVICES
    return list(set(packages))
