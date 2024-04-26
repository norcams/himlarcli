[![Build Status](https://travis-ci.org/norcams/himlarcli.svg?branch=master)](https://travis-ci.org/norcams/himlarcli)
# Himlar command line tool

## Examples

``` bash
cd himlarcli
source bin/activate
./hypervisor.py -h
```

## Development

Use virtualenv:

``` bash
cd himlarcli
virtualenv . -p /path/to/python3
source bin/activate
pip install --upgrade pip
# this is needed to install foreman module
pip install autosemver
python setup.py develop
pip install -r requirements.txt
```

### Config file

All script should have the `-c` option to set a custom config file. If this is
not set it will look for  `config.ini` in the root of himlarcli and then in
`/etc/himlarcli`

### pylint

We supply a .pylintrc file that are used for automated tests and code validation.
To check new or updated python files run:
``` bash
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

Example of /etc/hosts file: [Working with web services in vagrant](https://iaas.readthedocs.io/team/development/vagrant/web.html#working-with-web-services-in-vagrant)
