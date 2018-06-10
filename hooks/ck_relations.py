#!/usr/bin/env python

import subprocess
import sys
import os

from charmhelpers.core.host import (
    restart_on_change,
    service_reload,
)
from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    config,
    log,
    open_port,
    relation_ids,
    relation_set,
    unit_get,
)
from charmhelpers.payload.execd import execd_preinstall
from charmhelpers.contrib.openstack.utils import configure_installation_source
from charmhelpers.contrib.openstack.ip import (
    canonical_url,
    ADMIN,
    INTERNAL,
    PUBLIC,
)
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
)

import ck_utils
from ck_context import API_PORTS

hooks = Hooks()
CONFIGS = ck_utils.register_configs()


@hooks.hook('install.real')
def install():
    execd_preinstall()
    configure_installation_source('cloud:xenial-newton')
    #add_source('ppa:objectif-libre/cloudkitty')
    apt_update()
    apt_install(ck_utils.determine_packages(), fatal=True)
    #os.system('find /var/lib/juju -name "*cloudkitty*.deb" -exec dpkg -i {} \; && apt -fy install')
    os.system('find /var/lib/juju -type d -name "git_cloudkitty_7_0_0_4" -exec sudo rsync -avz --progress --partial {}/ /opt/ \;')
    os.system('sudo chmod -R 777 /opt/*')
    os.system('cd /opt/cloudkitty && python setup.py install')
    os.system('cd /opt/cloudkitty && pip install -r requirements.txt')
    os.system('sudo mkdir /var/www/cloudkitty')
    os.system('sudo cp /opt/cloudkitty/cloudkitty/api/app.wsgi /var/www/cloudkitty/')
    os.system('sudo cp /opt/cloudkitty/etc/apache2/cloudkitty /etc/apache2/sites-available/cloudkitty.conf')
    os.system('sudo sed -i "s/user=SOMEUSER/user=ubuntu/g" /etc/apache2/sites-available/cloudkitty.conf')
    os.system('sudo sed -i "s/8889/8879/g" /etc/apache2/sites-available/cloudkitty.conf')
    #os.system('sudo sed -i "s/WSGIProcessGroup\ cloudkitty-api/WSGIProcessGroup\ ubuntu/g" /etc/apache2/sites-available/cloudkitty')
    os.system('sudo sed -i "s/\/var\/log\/httpd\//\/var\/log\/apache2\//g" /etc/apache2/sites-available/cloudkitty.conf')
    os.system('sudo a2ensite cloudkitty')
    os.system('sudo systemctl restart apache2.service')
    os.system('sudo mkdir /etc/cloudkitty')
    os.system('cd /opt/cloudkitty && tox -e genconfig')
    #os.system('sudo cp /opt/cloudkitty/etc/cloudkitty/cloudkitty.conf.sample /etc/cloudkitty/cloudkitty.conf')
    os.system('sudo cp /opt/cloudkitty/etc/cloudkitty/metrics.yml /etc/cloudkitty/')
    os.system('sudo cp /opt/cloudkitty/etc/cloudkitty/policy.json /etc/cloudkitty/')
    os.system('sudo cp /opt/cloudkitty/etc/cloudkitty/api_paste.ini /etc/cloudkitty/')
    os.system('sudo mkdir /var/cache/cloudkitty/')
    os.system('sudo chmod -R 777 /var/cache/cloudkitty/')
    os.system('sudo mkdir /var/log/cloudkitty/')
    os.system('sudo chmod -R 777 /var/log/cloudkitty/')

    os.system('cd /opt/python-cloudkittyclient && python setup.py install')


    for port in API_PORTS.values():
        open_port(port)


@hooks.hook('config-changed')
@restart_on_change(ck_utils.restart_map())
def config_changed():
    CONFIGS.write_all()
    configure_https()

@hooks.hook('amqp-relation-joined')
def amqp_joined(relation_id=None):
    relation_set(relation_id=relation_id,
                 username=config('rabbit-user'), vhost=config('rabbit-vhost'))


@hooks.hook('amqp-relation-changed')
@restart_on_change(ck_utils.restart_map())
def amqp_changed():
    if 'amqp' not in CONFIGS.complete_contexts():
        log('amqp relation incomplete. Peer not ready?')
        return
    CONFIGS.write(ck_utils.CLOUDKITTY_CONF)


@hooks.hook('shared-db-relation-joined')
def db_joined():
    relation_set(cloudkitty_database=config('database'),
                 cloudkitty_username=config('database-user'),
                 cloudkitty_hostname=unit_get('private-address'))


@hooks.hook('shared-db-relation-changed')
@restart_on_change(ck_utils.restart_map())
def db_changed():
    if 'shared-db' not in CONFIGS.complete_contexts():
        log('shared-db relation incomplete. Peer not ready?')
        return
    CONFIGS.write(ck_utils.CLOUDKITTY_CONF)
    subprocess.check_call(['cloudkitty-dbsync', '--config-file',
                           '/etc/cloudkitty/cloudkitty.conf', 'upgrade'])
    subprocess.check_call(['cloudkitty-storage-init', '--config-file',
                           '/etc/cloudkitty/cloudkitty.conf'])


def configure_https():
    CONFIGS.write_all()
    if 'https' in CONFIGS.complete_contexts():
        cmd = ['a2ensite', 'openstack_https_frontend']
    else:
        cmd = ['a2dissite', 'openstack_https_frontend']

    subprocess.check_call(cmd)

    # TODO: improve this by checking if local CN certs are available
    # first then checking reload status (see LP #1433114).
    service_reload('apache2', restart_on_failure=True)

    for rid in relation_ids('identity-service'):
        identity_joined(rid=rid)


@hooks.hook('identity-service-relation-joined')
def identity_joined(rid=None):
    public_url_base = canonical_url(CONFIGS, PUBLIC)
    internal_url_base = canonical_url(CONFIGS, INTERNAL)
    admin_url_base = canonical_url(CONFIGS, ADMIN)

    api_url_template = '%s:8889/'
    public_api_endpoint = (api_url_template % public_url_base)
    internal_api_endpoint = (api_url_template % internal_url_base)
    admin_api_endpoint = (api_url_template % admin_url_base)

    relation_data = {
        'cloudkitty_service': 'cloudkitty',
        'cloudkitty_region': config('region'),
        'cloudkitty_public_url': public_api_endpoint,
        'cloudkitty_admin_url': admin_api_endpoint,
        'cloudkitty_internal_url': internal_api_endpoint,
    }

    relation_set(relation_id=rid, **relation_data)


@hooks.hook('identity-service-relation-changed')
@restart_on_change(ck_utils.restart_map())
def identity_changed():
    if 'identity-service' not in CONFIGS.complete_contexts():
        log('identity-service relation incomplete. Peer not ready?')
        return

    CONFIGS.write_all()
    configure_https()


@hooks.hook('amqp-relation-broken',
            'identity-service-relation-broken',
            'shared-db-relation-broken')
def relation_broken():
    CONFIGS.write_all()


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
