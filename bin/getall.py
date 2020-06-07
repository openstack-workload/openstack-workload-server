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

class Withless:
    r = None

    hosts_ram = {}
    allhosts = {}
    allhosts_load_sorted = []
    allhosts_data = {}
    allhosts_load = {}
    allhosts_vmcpu = {}
    allhosts_vmcpu_sorted = {}
    allhosts_info = {}

    vms = {}

    def connect(self):
        self.r = redis.Redis(
            host=           stackconfig.REDIS_SERVER,
            port=           stackconfig.REDIS_PORT,
            password=       stackconfig.REDIS_PASSWORD
        )


    def prepare(self):
        allhosts_json = {}
        self.allhosts = self.r.hkeys('hosts.lastminute')


        for host in self.allhosts:
            host_lastminute                 = self.r.hget('hosts.lastminute', host)
            host_key                        = 'hosts.json.' + host
            print(host, 'last minute:', host_lastminute)

            allhosts_json[host]             = self.r.hget(host_key, host_lastminute)
            self.allhosts_data[host]        = json.loads(allhosts_json[host])

            if self.allhosts_data[host] != None:
                self.allhosts_load[host]   = self.allhosts_data[host]['sys_info']['cpu_percent']




    #   'active_host':  None,
    #   'libvirtdata':  None,
    #   'piddata':      None,

    def sort_hosts_per_load(self):
        self.allhosts_load_sorted = sorted(self.allhosts_load.items(), key=operator.itemgetter(1))

    def get_ramstats_per_host(self, host):
        ram_total = 0
        ram_used = 0

        if host in self.allhosts_data:
            if 'kvm_procs' in self.allhosts_data[host]:
                for pid in self.allhosts_data[host]['kvm_procs']:
                    if 'libvirtdata' in self.allhosts_data[host]['kvm_procs'][pid]:
                        if 'memory' in self.allhosts_data[host]['kvm_procs'][pid]['libvirtdata']:
                            ram_used += int(self.allhosts_data[host]['kvm_procs'][pid]['libvirtdata']['memory']) * 1024 * 1024

        if host in self.allhosts_data:
            if 'sys_info' in self.allhosts_data[host]:
                if 'ram_total' in self.allhosts_data[host]['sys_info']:
                    ram_total = int(float(self.allhosts_data[host]['sys_info']['ram_total']))

        

        host_ram = {'total': ram_total, 'used': ram_used, 'free': ram_total - ram_used}
        self.hosts_ram[host] = host_ram
        return host_ram

    def allhosts_data_to_vms(self):

        for host in self.allhosts_data:
            self.allhosts_vmcpu[host] = {}

            host_data       = self.allhosts_data[host]
            host_sys        = host_data['sys_info']
            host_procs      = host_data['kvm_procs']
            #print(host, 'cores total:', host_sys['cores'], '% cpu:', host_sys['cpu_percent'], 'vms:', len(host_procs))

            for pid in host_procs:
                if 'libvirtdata' in host_procs[pid]:
                    vmdata                              = host_procs[pid]['libvirtdata']
                    uuid                                = vmdata['uuid']
                    self.vms[uuid]                      = {'host': host, 'vmdata': vmdata}

                    self.allhosts_vmcpu[host][uuid]     = host_procs[pid]['cputime_diff']

            vmcpu_sorted                                = sorted(self.allhosts_vmcpu[host].items(), key=operator.itemgetter(1))

            self.allhosts_vmcpu_sorted[host]            = vmcpu_sorted



            for host in self.allhosts_vmcpu_sorted:
                self.allhosts_info[host] = {}


                self.allhosts_info[host]['host_cores_total']      = self.allhosts_data[host]['sys_info']['cores']
                self.allhosts_info[host]['host_cpu_percent']      = self.allhosts_data[host]['sys_info']['cpu_percent']
                self.allhosts_info[host]['host_cores_free']       = (1.00 - (self.allhosts_data[host]['sys_info']['cpu_percent'] / 100.00)) * self.allhosts_data[host]['sys_info']['cores']
                self.allhosts_info[host]['host_ram_gb_used']      = float(self.allhosts_data[host]['sys_info']['ram_used']) / 1024 / 1024 / 1024
                self.allhosts_info[host]['host_ram_gb_free']      = float(self.allhosts_data[host]['sys_info']['ram_free']) / 1024 / 1024 / 1024
            

    # find a host that have free ram and cpu usage will not turn new host into top host
    def find_host_to_migrate(self, uuid):
        new_host = False

        if uuid in self.vms:
            active_host         = self.vms[uuid]['host']
            vm_ram_gb           = float(self.vms[uuid]['vmdata']['memory']) / float(1024.00)
            vm_vcpu             = float(self.vms[uuid]['vmdata']['vcpus'])
            active_host_info    = self.allhosts_info[active_host]
            

            for hostlist in self.allhosts_load_sorted:
                host = hostlist[0]

                host_info = self.allhosts_info[host]
                if host != active_host and new_host == False:
                    print(host, host_info['host_cores_free'], host_info['host_ram_gb_free'])
                    new_vcpu        = host_info['host_cores_free'] - vm_vcpu
                    new_ram_free    = host_info['host_ram_gb_free'] - vm_ram_gb
                    print("host new:", host, new_vcpu, new_ram_free)
                    print("host old", active_host, active_host_info['host_cores_free'], active_host_info['host_ram_gb_free'])
                    if new_vcpu < active_host_info['host_cores_free']:
                        print("new vcpu ok")
                        if new_ram_free > 16:
                            print("new ram ok")
                            new_host = host
                        else:
                            print("new ram not ok")
                    else:
                        print("new vcpu not ok")
        else:
            print("uuid not exist:", uuid)
            return False

        return new_host

    
    def find_vm_to_migrate(self, host, top = 10):
        vm = None

        print("trying to find a host destination from top", top, "to host:", host) 

        if host in self.allhosts_vmcpu_sorted:
            size = len(self.allhosts_vmcpu_sorted)
            if size >= top:
                vm = self.try_vm_to_migrate_n(host, top - 1) # try to migrate # top or 10
            else:
                vm = self.try_vm_to_migrate_n(host, size - 1) # try to migrate last one

        return vm

    def try_vm_to_migrate_n(self, host, n):
        vm = self.allhosts_vmcpu_sorted[host][n][0]
        print("vm to migrate", vm)
        return vm



wless = Withless()
wless.connect()
wless.prepare()
wless.sort_hosts_per_load()
wless.allhosts_data_to_vms()

host_first =            wless.allhosts_load_sorted[-1]
host_last =             wless.allhosts_load_sorted[0]
host_proc_diff =        float(float(host_first[1]) / float(host_last[1]) - 1)

pprint.pprint(wless.allhosts_load_sorted)
print("first:", host_first, "last:", host_last, "proc diff:", host_proc_diff)

if host_proc_diff > stackconfig.HOST_CPU_DIFF:
    cpu_diff_human = stackconfig.HOST_CPU_DIFF * 100
    print("diferenca entre primeira e ultima host maior que: ", cpu_diff_human, "%, vamos realizar uma migracao:", host_proc_diff)
    n = 1
    host_destination = False
    while n <= stackconfig.VM_EACH_LOOP and host_destination == False:
        top = n * stackconfig.VM_EACH_TOP
        print("\n\n")
        print("top:", top, "n:", n)

        vm_to_migrate       = wless.find_vm_to_migrate(host_first[0], top)
        host_destination    = wless.find_host_to_migrate(vm_to_migrate)
        n += 1
        print("final host destination:", host_destination, "vm to migrate:", vm_to_migrate)

for host in wless.allhosts:
    host_ram= wless.get_ramstats_per_host(host)

    print(
        "host:", host,
        "total:", bytes2human.bytes2human(wless.hosts_ram[host]['total']), 
        "used:", bytes2human.bytes2human(wless.hosts_ram[host]['used']),
        "free:", bytes2human.bytes2human(wless.hosts_ram[host]['free'])
    )




sys.exit(0)
                


"""for host in allhosts:
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
"""





