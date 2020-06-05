#!/usr/bin/python
import socket

import json
import pprint
import time
import bytes2human
import stackconfig
import datetime
import redis
import sys
import operator


r = redis.Redis(
    host=           stackconfig.REDIS_SERVER,
    port=           stackconfig.REDIS_PORT,
    password=       stackconfig.REDIS_PASSWORD
)


allhosts = r.hkeys('hosts.lastminute')

allhosts_json = {}
allhosts_data = {}
allhosts_load = {}

for host in allhosts:
    host_lastminute         = r.hget('hosts.lastminute', host)
    host_key                = 'hosts.json.' + host
    print(host, 'last minute:', host_lastminute)

    allhosts_json[host]     = r.hget(host_key, host_lastminute)
    allhosts_data[host]     = json.loads(allhosts_json[host])

    if allhosts_data[host] != None:
        allhosts_load[host]     = allhosts_data[host]['sys_info']['cpu_percent']
    
allhosts_load_sorted   = sorted(allhosts_load.items(), key=operator.itemgetter(1))

pprint.pprint(allhosts_load_sorted)


for host in allhosts:
    host_data       = allhosts_data[host]
    host_sys        = host_data['sys_info']
    host_procs      = host_data['kvm_procs']
    print(host, 'cores total:', host_sys['cores'], '% cpu:', host_sys['cpu_percent'], 'vms:', len(host_procs))

    pidcpu = {}
    for pid in host_procs:
        vmdata          = {}
        if 'libvirtdata' in host_procs[pid]:
            vmdata = host_procs[pid]['libvirtdata']
            #print vmdata


        pidcpu[pid] = host_procs[pid]['cputime_diff']

    pidcpu_sorted   = sorted(pidcpu.items(), key=operator.itemgetter(1))
    
    n = 1
    while n <= 10:
        print(pidcpu_sorted[-n])
        pid = pidcpu_sorted[-n][0]
        #print(host_procs[pid]['libvirtdata'])
        pprint.pprint(host_procs[pid])
        n += 1


    print("#####################################\n\n")
