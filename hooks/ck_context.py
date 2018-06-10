from charmhelpers.contrib.openstack import context
from charmhelpers.contrib.hahelpers.cluster import (
    determine_apache_port,
    determine_api_port,
)

API_PORTS = {
    'cloudkitty-api': 8889,
}


class CloudkittyHAProxyContext(context.OSContextGenerator):
    interfaces = ['cloudkitty-haproxy']

    def __call__(self):
        """Extends the main charmhelpers HAProxyContext with a port mapping
        specific to this charm.
        Also used to extend cinder.conf context with correct api_listening_port
        """
        haproxy_port = API_PORTS['cloudkitty-api']
        api_port = determine_api_port(haproxy_port, singlenode_mode=True)
        apache_port = determine_apache_port(haproxy_port, singlenode_mode=True)

        ctxt = {
            'service_ports': {'cloudkitty_api': [haproxy_port, apache_port]},
            'api_listen_port': api_port,
        }
        return ctxt


class CloudkittyApacheSSLContext(context.ApacheSSLContext):

    external_ports = API_PORTS.values()
    service_namespace = 'cloudkitty'
