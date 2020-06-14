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




wless.slog.p("################## cluster info")
for item in wless.allhosts_load_sorted:
    host =                  item[0]
    load_percentual =       item[1]

    host_ram= wless.get_ramstats_per_host(host)

    wless.slog.p("host {host}".format(host=host))
    wless.slog.p("{0:>15s}: {1:s}".format("ram_total", bytes2human.bytes2human(wless.hosts_ram[host]['total'])))
    wless.slog.p("{0:>15s}: {1:s}".format("ram_used", bytes2human.bytes2human(wless.hosts_ram[host]['used'])))
    wless.slog.p("{0:>15s}: {1:s}".format("ram_free", bytes2human.bytes2human(wless.hosts_ram[host]['free'])))
    wless.slog.p("{0:>15s}: {1:0.2f}%".format("cpu_percentual", load_percentual))
    wless.slog.p("{0:>15s}: {1:0d}".format("cpu_total", wless.allhosts_data[host]['sys_info']['cores']))
    wless.slog.p("{0:>15s}: {1:0.2f}".format("cpu_total", wless.allhosts_info[host]['host_cores_free']))
    wless.slog.p("")


wless.slog.p("################## end cluster info")
wless.slog.p("\n\n")


#HOST_CPU_MAX
host_first_name     = host_first[0]
host_first_cpu      = host_first[1]

if (host_first_cpu / 100) >= stackconfig.HOST_CPU_MAX:
    cpu_diff_human = stackconfig.HOST_CPU_DIFF * 100

    wless.slog.p("################## run info")
    wless.slog.p("necessario rodar balanceamento - cpu usada no host {2:s} {1:0.2f}% maior que o limite {0:0.2f}%".format(
        stackconfig.HOST_CPU_MAX * 100,
        host_first_cpu,
        host_first_name
    ))
    wless.slog.p("################## end run info")
    wless.slog.p("\n\n")



    n = stackconfig.VM_EACH_TOP_JUMP
    host_destination = False
    while n <= stackconfig.VM_EACH_LOOP and host_destination == False:
        top = n * stackconfig.VM_EACH_TOP
        wless.slog.p("\n\n")
        wless.slog.p("top: {top} n: {n}".format(top=top, n=n))

        vm_to_migrate       = wless.find_vm_to_migrate(host_first[0], top)
        if wless.is_blacklisted(vm_to_migrate) == False:
            host_destination    = wless.find_host_to_migrate(vm_to_migrate)
            wless.slog.p("final host destination: {dest} vm to migrate: {vm}".format(
                dest=host_destination,
                vm=vm_to_migrate
            ))
        else:
            wless.slog.p("vm blacklisted {vm}".format(vm=vm_to_migrate))
            
        n += 1

        if host_destination != False:
            wless.slog.p("\n\n")
            wless.slog.p("################## run manually")
            wless.slog.p("source /opt/stackwithless/bin/openstack-rc.sh")
            wless.slog.p("openstack server migrate {vm} --live {host}.localdomain".format(host=host_destination, vm=vm_to_migrate))
            wless.slog.p("################## end run manually")
            wless.slog.logresult("migrated", host_old=host_first_name, host_new=host_destination, vm=vm_to_migrate)
            wless.blacklist(vm_to_migrate, stackconfig.VM_BLACKLIST_SECS)
   
else:
    wless.slog.p("################## run info")
    wless.slog.p("nao rodar balanceamento - cpu usada no host {2:s} {1:0.2f}% menor que o limite {0:0.2f}%".format(
        stackconfig.HOST_CPU_MAX * 100,
        host_first_cpu,
        host_first_name
    ))
    wless.slog.p("################## end run info")
    wless.slog.p("\n\n")
    wless.slog.logresult("not_needed_less_than_max_cpu", host_old=host_first_name, host_new=None, vm=None)


wless.slog.close()



