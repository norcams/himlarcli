[![Build Status](https://travis-ci.org/norcams/himlarcli.svg?branch=master)](https://travis-ci.org/norcams/himlarcli)
# Himlar command line tool

## Examples

```bash
cd himlarcli
source bin/activate
./host.py -h
```

## Development

You will need to install some OS packages. Example for packages
needed for CentOS 7 can be found here:

https://github.com/norcams/ansible/blob/master/lib/deploy_himlarcli.yaml

Use virtualenv:

```bash
cd himlarcli
virtualenv .
source bin/activate
pip install setuptools==44.1.1
python setup.py develop
pip install -r requirements.txt
```

### Install on CentOS 7

Requirements
```
yum install -y python-virtualenv PyYAML openldap-devel openssl-devel gcc
```
After virtualenv run
```
pip install --upgrade setuptools
```

### Config file

All script should have the `-c` option to set a custom config file. If this is
not set it will look for  `config.ini` in the root of himlarcli and then in
`/etc/himlarcli`

### pylint

We supply a .pylintrc file that are used for automated tests and code validation.
To check new or updated python files run:
```
pytlint <script>.py
```
or to run the full test travis uses with `test.sh`

#### disable

“#pylint: disable=some-message,another-one” at the desired block level or at the
end of the desired line of code. You can disable messages either by code or by
symbolic name.

### Vagrant

This is for use with himlar in vagrant.

#### Config

Use config.ini.example and remember to change keystone_cachain: with
path to root CA used in vagrant

If you have a `config.ini` in the himlarcli root directory it will use this
automatically in all scripts.

#### Dataporten access

If the vagrant installation is setup with support for Dataporten login
you can use `access.py` to provision the user and project without the need
to install the access node:

```
./access.py push --email <feide-email> --password <password>
./access.py pop --debug
```

exit the last script after the user is created.

*NOTE*: Make sure the rabbitmq section is present in your config.ini first!

#### Hosts

This is for use in /etc/hosts in vagrant

```bash
# vagrant public
192.168.0.252   access.vagrant.iaas.intern
192.168.0.254   dashboard.vagrant.iaas.intern
192.168.0.250   status.vagrant.iaas.intern
192.168.0.250   api.vagrant.iaas.intern
192.168.0.250   compute.api.vagrant.iaas.intern
192.168.0.250   network.api.vagrant.iaas.intern
192.168.0.250   image.api.vagrant.iaas.intern
192.168.0.250   identity.api.vagrant.iaas.intern
192.168.0.250   volume.api.vagrant.iaas.intern

# vagrant trp
172.31.8.81     identity.trp.vagrant.iaas.intern
172.31.8.86     compute.trp.vagrant.iaas.intern
172.31.8.86     network.trp.vagrant.iaas.intern

# vagrant mgmt
172.31.0.11     foreman.mgmt.vagrant.iaas.intern
```
