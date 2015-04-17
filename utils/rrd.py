#!/usr/bin/python
import urllib
import rrdtool
import os
from helper_functions import get_ends, get_carrier
from oam_multiconnect import get_graph_data

rrd_dir = os.path.join('/'.join(os.path.abspath(__file__).split('/')[:-2]), 'rrd')

DATASOURCE_DICT = {
    'average_twoway_delay_variation': 'av2dv',
    'average_twoway_delay': 'av2d',
    'bestcase_twoway_delay': 'b2d',
    'worstcase_twoway_delay': 'w2d'
}


def update_delay(name, average_twoway_delay, bestcase_twoway_delay, worstcase_twoway_delay, step=300):
    if not os.path.exists('%s-delay.rrd' % os.path.join(rrd_dir, name)):
        rrdtool.create(
            '%s-delay.rrd' % str(os.path.join(rrd_dir, name)),
            '--step',
            str(step),
            '--start',
            '0',
            'DS:%s:GAUGE:%s:U:U' % (DATASOURCE_DICT['average_twoway_delay'], step + 300),
            'DS:%s:GAUGE:%s:U:U' % (DATASOURCE_DICT['bestcase_twoway_delay'], step + 300),
            'DS:%s:GAUGE:%s:U:U' % (DATASOURCE_DICT['worstcase_twoway_delay'], step + 300),
            'RRA:AVERAGE:0.5:1:300',
            'RRA:AVERAGE:0.5:6:700',
            'RRA:AVERAGE:0.5:24:775',
            'RRA:AVERAGE:0.5:288:797',
            'RRA:MAX:0.5:1:600',
            'RRA:MAX:0.5:6:700',
            'RRA:MAX:0.5:24:775',
            'RRA:MAX:0.5:444:797'
        )
    rrdtool.update(
        '%s-delay.rrd' % str(os.path.join(rrd_dir, name)),
        'N:%s:%s:%s' % (
            str(average_twoway_delay),
            str(bestcase_twoway_delay),
            str(worstcase_twoway_delay)
        )
    )


def update_jitter(name, average_twoway_delay_variation, step=300):
    if not os.path.exists('%s-jitter.rrd' % os.path.join(rrd_dir, name)):
        rrdtool.create(
            '%s-jitter.rrd' % str(os.path.join(rrd_dir, name)),
            '--step',
            str(step),
            '--start',
            '0',
            'DS:%s:GAUGE:%s:U:U' % (DATASOURCE_DICT['average_twoway_delay_variation'], step + 300),
            'RRA:AVERAGE:0.5:1:300',
            'RRA:AVERAGE:0.5:6:700',
            'RRA:AVERAGE:0.5:24:775',
            'RRA:AVERAGE:0.5:288:797',
            'RRA:MAX:0.5:1:600',
            'RRA:MAX:0.5:6:700',
            'RRA:MAX:0.5:24:775',
            'RRA:MAX:0.5:444:797'
        )
    rrdtool.update(
        '%s-jitter.rrd' % str(os.path.join(rrd_dir, name)),
        'N:%s' % (
            str(average_twoway_delay_variation),
        )
    )


def update_rrds():
    devices = get_carrier()
    for k, v in get_graph_data(devices).items():
        update_delay(k, v['average-twoway-delay'], v['bestcase-twoway-delay'], v['worstcase-twoway-delay'])
        update_jitter(k, v['average-twoway-delay-variation'])


def create_graphs_for_host(host, start, end):
    graphs = []
    devices = get_ends()
    for device, md in devices.items():
        if device.lower() == host:
            for domain in md:
                name = '%s_%s' % (device.lower(), domain['md_name'])
                graphs.append({
                    domain['md_name']:
                    {
                        'delay': create_delay_graph(name, start, end),
                        'jitter': create_jitter_graph(name, start, end),
                    }
                })
            break
    return graphs


def create_delay_graph(name, start, end):
    if os.path.exists('%s-delay.rrd' % os.path.join(rrd_dir, name)):
        graph_name = '%s-delay.png' % (
            str('/tmp/%s' % name),
        )
        rrdtool.graph(
            graph_name,
            '--start',
            str(start),
            '--end',
            str(end),
            '-X -1',
            '--vertical-label=us',
            'DEF:m1_num=%s-delay.rrd:%s:AVERAGE' % (str(os.path.join(rrd_dir, name).replace(':', '\:')), DATASOURCE_DICT['average_twoway_delay']),
            'DEF:m2_num=%s-delay.rrd:%s:AVERAGE' % (str(os.path.join(rrd_dir, name).replace(':', '\:')), DATASOURCE_DICT['bestcase_twoway_delay']),
            'DEF:m3_num=%s-delay.rrd:%s:AVERAGE' % (str(os.path.join(rrd_dir, name).replace(':', '\:')), DATASOURCE_DICT['worstcase_twoway_delay']),
            'AREA:m1_num#b2cde0:%s\l' % ('average twoway delay'),
            'LINE2:m2_num#41ca41:%s\l' % ('bestcase twoway delay'),
            'LINE3:m3_num#dd46a9:%s\l' % ('worstcase twoway delay'),
        )
        with open(graph_name, 'r') as f:
            resp = {
                'name': name.split('_')[0],
                'img': urllib.quote(f.read().encode('base64')),
            }
        return resp


def create_jitter_graph(name, start, end):
    if os.path.exists('%s-jitter.rrd' % os.path.join(rrd_dir, name)):
        graph_name = '%s-jitter.png' % (
            str('/tmp/%s' % name)
        )
        rrdtool.graph(
            graph_name,
            '--start',
            str(start),
            '--end',
            str(end),
            '-X -1',
            '--vertical-label=us',
            'DEF:av_num=%s-jitter.rrd:%s:AVERAGE' % (str(os.path.join(rrd_dir, name).replace(':', '\:')), DATASOURCE_DICT['average_twoway_delay_variation']),
            'AREA:av_num#41ca41:%s\l' % 'average twoway delay variation'
        )
        with open(graph_name, 'r') as f:
            resp = {
                'name': name.split('_')[0],
                'img': urllib.quote(f.read().encode('base64')),
            }
        return resp
