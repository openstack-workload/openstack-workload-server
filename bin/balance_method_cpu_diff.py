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
from stack import Withless 


wless = Withless()
wless.connect()
wless.prepare()
wless.sort_hosts_per_load()
wless.allhosts_data_to_vms()

host_first =            wless.allhosts_load_sorted[-1]
host_last =             wless.allhosts_load_sorted[0]
host_proc_diff =        float(float(host_first[1]) / float(host_last[1]) - 1)




print("################## cluster info")
for item in wless.allhosts_load_sorted:
    host =                  item[0]
    load_percentual =       item[1]

    host_ram= wless.get_ramstats_per_host(host)

    """print(
        "host:", host,
        "ram_total:", bytes2human.bytes2human(wless.hosts_ram[host]['total']), 
        "ram_used:", bytes2human.bytes2human(wless.hosts_ram[host]['used']),
        "ram_free:", bytes2human.bytes2human(wless.hosts_ram[host]['free']),
        "cpu_percentual:", load_percentual,
        "cpu_total:", wless.allhosts_data[host]['sys_info']['cores'],
        "cpu_free:", wless.allhosts_info[host]['host_cores_free']
    )"""

    print("host {host}".format(host=host))
    print("{0:>15s}: {1:s}".format("ram_total", bytes2human.bytes2human(wless.hosts_ram[host]['total'])))
    print("{0:>15s}: {1:s}".format("ram_used", bytes2human.bytes2human(wless.hosts_ram[host]['used'])))
    print("{0:>15s}: {1:s}".format("ram_free", bytes2human.bytes2human(wless.hosts_ram[host]['free'])))
    print("{0:>15s}: {1:0.2f}%".format("cpu_percentual", load_percentual))
    print("{0:>15s}: {1:0d}".format("cpu_total", wless.allhosts_data[host]['sys_info']['cores']))
    print("{0:>15s}: {1:0.2f}".format("cpu_total", wless.allhosts_info[host]['host_cores_free']))
    print("")


print("################## end cluster info")
print("\n\n")


if host_proc_diff > stackconfig.HOST_CPU_DIFF:
    cpu_diff_human = stackconfig.HOST_CPU_DIFF * 100

    print("################## run info")
    print("necessario rodar balanceamento - diferenca entre primeira e ultima host maior que {0:0.2f}% : {1:0.2f}%".format(
        stackconfig.HOST_CPU_DIFF * 100,
        host_proc_diff * 100
    ))
    print("################## end run info")
    print("\n\n")



    n = stackconfig.VM_EACH_TOP_JUMP
    host_destination = False
    while n <= stackconfig.VM_EACH_LOOP and host_destination == False:
        top = n * stackconfig.VM_EACH_TOP
        print("\n\n")
        print("top:", top, "n:", n)

        vm_to_migrate       = wless.find_vm_to_migrate(host_first[0], top)
        host_destination    = wless.find_host_to_migrate(vm_to_migrate)
        n += 1
        print("final host destination:", host_destination, "vm to migrate:", vm_to_migrate)

    if host_destination != False:
        print("\n\n")
        print("################## run manually")
        print("cli:")
        print("source /opt/stackwithless/bin/openstack-rc.sh")
        print("openstack server migrate {vm} --live {host}.localdomain".format(host=host_destination, vm=vm_to_migrate))
        print("################## end run manually")
    
else:
    print("################## run info")

    print("nao rodar balanceamento - diferenca entre primeira e ultima host menor que {0:0.2f}% : {1:0.2f}%".format(
        stackconfig.HOST_CPU_DIFF * 100,
        host_proc_diff * 100
    ))
    print("################## end run info")
    print("\n\n")






