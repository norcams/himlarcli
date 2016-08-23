images = dict()
images['centos'] = {
    'name':             'CentOS 7',
    'url':              'http://cloud.centos.org/centos/7/images/',
    'latest':           'CentOS-7-x86_64-GenericCloud.qcow2',
    'checksum_file':    'sha256sum.txt',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}

images['fedora'] = {
    'name':             'Fedora 24',
    'url':              'https://www.mirrorservice.org/sites/dl.fedoraproject.org/pub/fedora/linux/releases/24/CloudImages/x86_64/images/',
    'latest':           'Fedora-Cloud-Base-24-1.2.x86_64.qcow2',
    'checksum_file':    'Fedora-CloudImages-24-1.2-x86_64-CHECKSUM',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}

images['ubuntu'] = {
    'name':             'Ubuntu server 16.04',
    'url':              'https://cloud-images.ubuntu.com/xenial/current/',
    'latest':           'xenial-server-cloudimg-amd64-disk1.img',
    'checksum_file':    'SHA256SUMS',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}

images['debian'] = {
    'name':             'Debian Jessie 8.5',
    'url':              'http://cdimage.debian.org/cdimage/openstack/current/',
    'latest':           'debian-8.5.0-openstack-amd64.qcow2',
    'checksum_file':    'SHA256SUMS',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}
