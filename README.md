Cloudkitty Charm for Juju enviroment
========
![Alt text](icon.svg?raw=true "Cloudkitty Logo")

Overview
========

CloudKitty is the Rating-as-a-Service component for OpenStack. It provides an
API to configure pricing policy and retrieve billing information.

This charm deploys the CloudKitty infrastructure.

Usage
=====

CloudKitty requires the following charms to be fully functional:

* mysql
* rabbitmq-server
* keystone

Deploy
=======

To deploy our charm from local repository we have to create a folder and upload our charm then:

    juju deploy /home/openstack/juju-charm/cloudkitty-charm --to 0/lxd/38
    juju add-relation cloudkitty-charm mysql
    juju add-relation cloudkitty-charm rabbitmq-server
    juju add-relation cloudkitty-charm keystone

Give the rating role to cloudkitty for each project that should be handled by cloudkitty:

    openstack role create rating
    openstack role add --project XXX --user cloudkitty rating



Install Dashboard
=======

Our charm only install cloudkitty service, we have to install dashboard module to our Horizon Panel

    cd /opt/
    sudo git clone https://git.openstack.org/openstack/cloudkitty-dashboard.git
    cd cloudkitty-dashboard
    sudo python setup.py install
    sudo pip install -r requirements.txt
    PY_PACKAGES_PATH=`pip --version | cut -d' ' -f4`
    sudo ln -sf /opt/cloudkitty-dashboard/cloudkittydashboard/enabled/_[0-9]*.py $PY_PACKAGES_PATH/openstack_dashboard/enabled/
    sudo ln -sf /opt/cloudkitty-dashboard/cloudkittydashboard/enabled/_[0-9]*.py /usr/share/openstack-dashboard/openstack_dashboard/enabled/
    sudo systemctl restart $(systemctl list-unit-files | grep openstack-dashboard | awk '{print $1}')



Contact
=======

Charm Author: Adrian Campos <adriancampos@teachelp.com>
