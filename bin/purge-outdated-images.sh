#!/bin/bash

images_vgpu=(
    centos7
    vgpu_centos8
    almalinux8
    almalinux9
    almalinux10
    ubuntu_2004
    ubuntu_2204
    ubuntu_2404
)

images_uio=(
    uio_rhel7
    uio_rhel8
    uio_rhel9
)

images_uib=(
    rockylinux8_uib_puppet
)

images_gold=(
    ubuntu_1604
    ubuntu_1804
    ubuntu_1904
    ubuntu_1910
    ubuntu_2104
    ubuntu_2110
    ubuntu_2004
    ubuntu_2204
    ubuntu_2404
    fedora_27
    fedora_28
    fedora_29
    fedora_30
    fedora_31
    fedora_32
    fedora_33
    fedora_34
    fedora_35
    fedora_36
    fedora_37
    fedora_38
    fedora_39
    fedora_40
    fedora_41
    fedora_42
    debian9
    debian10
    debian11
    debian12
    debian13
    centos6
    centos7
    centos8
    centosstream8
    centosstream9
    centosstream10
    almalinux8
    almalinux9
    almalinux10
    rockylinux8
    rockylinux9
    rockylinux10
    winsrv2019core
    winsrv2019std
    winsrv2022std
    winsrv2025std
)

# vGPU images
for image in ${images_vgpu[@]}; do
    echo "Deleting unused deactivated images with name: $image"
    ./image.py purge -n $image -t vgpu -v shared --force
    if [ "$?" != "0" ]; then
	echo "ERROR: Something went wrong!"
	exit 1
    fi
    echo "Usage:"
    ./image.py usage -n $image -t vgpu -v shared -s deactive
done

# UiO images
for image in ${images_uio[@]}; do
    echo "Deleting unused deactivated images with name: $image"
    ./image.py purge -n $image -t uio -v shared --force
    if [ "$?" != "0" ]; then
	echo "ERROR: Something went wrong!"
	exit 1
    fi
    echo "Usage:"
    ./image.py usage -n $image -t uio -v shared -s deactive
done

# UiB images
for image in ${images_uib[@]}; do
    echo "Deleting unused deactivated images with name: $image"
    ./image.py purge -n $image -t uib -v shared --force
    if [ "$?" != "0" ]; then
	echo "ERROR: Something went wrong!"
	exit 1
    fi
    echo "Usage:"
    ./image.py usage -n $image -t uib -v shared -s deactive
done

# Public images
for image in ${images_gold[@]}; do
    echo "Deleting unused deactivated images with name: $image"
    ./image.py purge -n $image -t gold -v public --force
    if [ "$?" != "0" ]; then
	echo "ERROR: Something went wrong!"
	exit 1
    fi
    echo "Usage:"
    ./image.py usage -n $image -t gold -v public -s deactive
done
