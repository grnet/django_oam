#!/usr/bin/env python
from ncclient import manager
import nxpy as np
from lxml import objectify
import socket
from django.conf import settings


def icinga_query(md, ma, local, remote):
    return '''
            <get-cfm-mep-database>
                    <maintenance-domain>%s</maintenance-domain>
                    <maintenance-association>%s</maintenance-association>
                    <local-mep>%s</local-mep>
                    <remote-mep>%s</remote-mep>
            </get-cfm-mep-database>
        ''' % (md, ma, local, remote)


def sla_iter_rpc_query(md, ma, local, remote, sla='delay-measurement'):
    return '''
        <get-cfm-iterator-statistics>
                <sla-iterator>%s</sla-iterator>
                <maintenance-domain>%s</maintenance-domain>
                <maintenance-association>%s</maintenance-association>
                <local-mep>%s</local-mep>
                <remote-mep>%s</remote-mep>
        </get-cfm-iterator-statistics>
    ''' % (sla, md, ma, local, remote)


def graph_data(host):
    results = {}
    with manager.connect(host=host, username=settings.NETCONF_USERNAME, password=settings.NETCONF_PASSWORD, hostkey_verify=False, port=22, device_params={"name": "junos"}) as m:
        xmlconfig = m.get_config(source='running').tostring
        parser = np.Parser()
        parser.confile = xmlconfig
        device = parser.export()
        checks = {}
        checks[host] = []
        for i in device.protocols['oam'].ethernet.connectivity_fault_management.maintenance_domains:
            md_name = i.name
            ma = i.maintenance_association
            ma_name = ma.name
            mep_name = ma.mep['name']
            if ma.mep['remote_mep']['name']:
                remotemep_name = ma.mep['remote_mep']['name']
                if ma.mep['remote_mep']['sla_iterator_profiles']:
                    for sla_iter in ma.mep['remote_mep']['sla_iterator_profiles']:
                        checks[host].append({"md": md_name, "ma": ma_name, "local_mep": mep_name, "remote_mep": remotemep_name, "sla_iter": sla_iter})
        if checks[host]:
            for check in checks[host]:
                rpc_query = sla_iter_rpc_query(check['md'], check['ma'], check['local_mep'], check['remote_mep'])
                result = m.rpc(rpc_query)
                rootobj = objectify.fromstring(result.tostring)
                found = 0
                try:
                    stats = rootobj
                    found = 1
                except:
                    pass
                try:
                    stats = rootobj['cfm-iterator-statistics']['cfm-entry']['cfm-iter-ethdm-entry']
                    found = 1
                except:
                    pass
                if not found:
                    continue
                header = "%s_%s" % (str(socket.gethostbyaddr(host)[0]).lower(), check['md'])
                results.update({header: stats.__dict__})
    return results


def workon(host):
    results = {}
    with manager.connect(host=host, username=settings.NETCONF_USERNAME, password=settings.NETCONF_PASSWORD, hostkey_verify=False, port=22, device_params={"name": "junos"}) as m:
        xmlconfig = m.get_config(source='running').tostring
        parser = np.Parser()
        parser.confile = xmlconfig
        device = parser.export()
        checks = {}
        checks[host] = []
        for i in device.protocols['oam'].ethernet.connectivity_fault_management.maintenance_domains:
            md_name = i.name
            ma = i.maintenance_association
            ma_name = ma.name
            mep_name = ma.mep['name']
            if ma.mep['remote_mep']['name']:
                remotemep_name = ma.mep['remote_mep']['name']
                if ma.mep['remote_mep']['sla_iterator_profiles']:
                    for sla_iter in ma.mep['remote_mep']['sla_iterator_profiles']:
                        checks[host].append({"md": md_name, "ma": ma_name, "local_mep": mep_name, "remote_mep": remotemep_name, "sla_iter": sla_iter})
        if checks[host]:
            for check in checks[host]:
                rpc_query = icinga_query(check['md'], check['ma'], check['local_mep'], check['remote_mep'])
                result = m.rpc(rpc_query)
                rootobj = objectify.fromstring(result.tostring)
                found = 0
                try:
                    stats = rootobj
                    found = 1
                except:
                    pass
                try:
                    stats = rootobj['cfm-mep-database']['cfm-entry']['cfm-remote-meps']['cfm-remote-mep']['cfm-remote-mep-state']
                    found = 1
                except:
                    pass
                if not found:
                    continue
                header = "%s_%s" % (socket.gethostbyaddr(host)[0], check['md'])
                results.update({header: stats})
    return results
