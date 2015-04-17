import json
from django.http import HttpResponse
from django.shortcuts import render
from utils.oam_multiconnect import oam_icinga_config
from utils.rrd import create_graphs_for_host
from utils.helper_functions import get_ends


def icinga(request):
    response = oam_icinga_config(request.GET.get('with_hosts'))
    return HttpResponse(response, content_type="text/plain")


def graphs(request, node_name):
    start = request.GET.get('start', '-1500')
    end = request.GET.get('end', '-300')
    result = create_graphs_for_host(node_name, start, end)
    # rest api
    if request.GET.get('format') == 'json':
        return HttpResponse(json.dumps(result), content_type='application/json')
    else:
        return render(request, 'oam/frontend/graphs.html', {'graphs': result})


def nodes(request):
    result = get_ends().keys()
    return HttpResponse(json.dumps(result), content_type='application/json')
