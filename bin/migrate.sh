#!/bin/bash

args=("$@")
source /opt/stackwithless/bin/openstack-rc.sh
echo openstack server migrate ${args[0]} --live ${args[1]}
