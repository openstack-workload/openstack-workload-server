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
from slog import slog



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
    slog = None
    

    def __init__(self):
        self.slog = slog()

    def connect(self):
        self.r = redis.Redis(
            host=           stackconfig.REDIS_SERVER,
            port=           stackconfig.REDIS_PORT,
            password=       stackconfig.REDIS_PASSWORD
        )

    def blacklist(self, vm, seconds=stackconfig.VM_BLACKLIST_SECS):
        eol=int(time.time()) + seconds
        self.r.hset("vm_blacklist", vm, eol)

    def is_blacklisted(self, vm):
        eol=self.r.hget("vm_blacklist", vm)

        if eol == None:
            return False

        eol=int(eol)
        n = int(time.time())
        if eol > n:
            return True

        return False


    def prepare(self):
        allhosts_json = {}
        self.allhosts = self.r.hkeys('hosts.lastminute')

        self.slog.p("################## time check")
        for host in self.allhosts:
            host_lastminute                 = self.r.hget('hosts.lastminute', host)
            host_key                        = 'hosts.json.' + host
            self.slog.p("host {host} - last minute: {minute}".format(host=host, minute=host_lastminute))
            allhosts_json[host]             = self.r.hget(host_key, host_lastminute)
            self.allhosts_data[host]        = json.loads(allhosts_json[host])

            if self.allhosts_data[host] != None:
                self.allhosts_load[host]   = self.allhosts_data[host]['sys_info']['cpu_percent']


        self.slog.p("################## time check end")
        self.slog.p("\n\n")



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
            #self.slog.p(host, 'cores total:', host_sys['cores'], '% cpu:', host_sys['cpu_percent'], 'vms:', len(host_procs))

            for pid in host_procs:
                if 'libvirtdata' in host_procs[pid]:
                    vmdata                              = host_procs[pid]['libvirtdata']
                    uuid                                = vmdata['uuid']
                    self.vms[uuid]                      = {'host': host, 'vmdata': vmdata, 'process' : host_procs[pid]}

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
            vm_vcpu_usage       = float(self.vms[uuid]['process']['cputime_diff'])

            active_host_info    = self.allhosts_info[active_host]
            

            for hostlist in self.allhosts_load_sorted:
                host = hostlist[0]

                host_info = self.allhosts_info[host]
                if host != active_host and new_host == False:
                    self.slog.p("host {host} cores free {cores} ram free {ram}".format(host=host, cores=host_info['host_cores_free'], ram=host_info['host_ram_gb_free']))
                    new_vcpu_free       = host_info['host_cores_free'] - vm_vcpu_usage
                    new_ram_free        = host_info['host_ram_gb_free'] - vm_ram_gb
                    old_vcpu_free       = active_host_info['host_cores_free'] + vm_vcpu_usage

                    self.slog.p("host new: {host} vcpu free: {vcpu} ram free: {ram}".format(host=host, vcpu=new_vcpu_free, ram=new_ram_free))
                    self.slog.p("host old: {host} vcpu free: {vcpu} ram free: {ram}".format(host=active_host, vcpu=active_host_info['host_cores_free'], ram=active_host_info['host_ram_gb_free']))

                    if new_vcpu_free > old_vcpu_free:
                        self.slog.p("new vcpu ok")
                        if new_ram_free > 16:
                            self.slog.p("new ram ok")
                            new_host = host
                        else:
                            self.slog.p("new ram not ok")
                    else:
                        self.slog.p("new vcpu not ok: {host} vcpu free: {vcpu} old vcpu free: {vcpu_old}".format(vcpu=new_vcpu_free, vcpu_old=active_host_info['host_cores_free'], host=host))
        else:
            self.slog.p("uuid not exist: {uuid}".format(uuid=uuid))
            return False

        return new_host

    
    def find_vm_to_migrate(self, host, top = 10):
        vm = None

        self.slog.p("trying to find a host destination from top {top} to host {host}".format(top=top, host=host))

        if host in self.allhosts_vmcpu_sorted:
            size = len(self.allhosts_vmcpu_sorted[host])
            if size >= top:
                vm = self.try_vm_to_migrate_n(host, top - 1) # try to migrate # top or 10
            else:
                vm = self.try_vm_to_migrate_n(host, size - 1) # try to migrate last one

        return vm

    def try_vm_to_migrate_n(self, host, n):
        vm = self.allhosts_vmcpu_sorted[host][n][0]
        self.slog.p("vm to migrate: " + vm)
        return vm




