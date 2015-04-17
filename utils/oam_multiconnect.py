import time
import socket
import os
from django.template.loader import render_to_string
from django.conf import settings
from monitor import workon, graph_data
from utils.helper_functions import get_ends


def oam_icinga_config(with_hosts):
    config = ''
    mds = []
    vpns = get_ends()
    for node in vpns:
        if with_hosts:
            config += render_to_string(
                'oam/host.cfg',
                {
                    'hostname': node,
                    'address': socket.gethostbyname(node)
                }
            )
        for vpn in vpns[node]:
            if vpn['md_name'] in mds:
                continue
            config += render_to_string(
                'oam/service.cfg',
                {
                    'host': node.lower(),
                    'maintenance_domain': vpn['md_name'].replace(':', '@')
                }
            )
            mds.append(vpn['md_name'])
    config += render_to_string(
        'oam/command.cfg',
        {}
    )
    return config


def commit_results(res):
    for header, val in res.items():
        host_name = header.split('_')[0]
        if val == 'ok':
            code = 0
        else:
            code = 1
        result = render_to_string(
            'oam/result.txt',
            {
                'now': int(time.time()),
                'host': host_name.lower(),
                'service': 'OAM_%s' % (header.replace(':', '@').replace(host_name, host_name.lower())),
                'result': val,
                'code': code,
                'icinga_host': settings.ICINGA_SERVER
            }
        )
        os.system(result)


def get_graph_data(hosts):
    result = {}
    for host in hosts:
        try:
            res = graph_data(host)
        except:
            continue
        for k, v in res.items():
            try:
                result.update({
                    k: {
                        'average-twoway-delay-variation': v['cfm-average-twoway-delay-variation'],
                        'average-twoway-delay': v['cfm-average-twoway-delay'],
                        'bestcase-twoway-delay': v['cfm-bestcase-twoway-delay'],
                        'worstcase-twoway-delay': v['cfm-worstcase-twoway-delay']
                    }
                })
            except:
                print 'could not find data for %s' % host
                continue
    return result


def icinga_stats(hosts):
    # amount_of_workers = 6
    for host in hosts:
        device = socket.gethostbyname(host)
        commit_results(workon(device))
