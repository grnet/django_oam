# -*- coding: utf-8 -*- vim:encoding=utf-8:
from django.conf.urls.defaults import url, patterns

urlpatterns = patterns(
    'views',
    url(r'^icinga/$', 'icinga', name='icinga'),
    url(r'^nodes/$', 'nodes', name='oam_nodes'),
    url(r'^(?P<node_name>[\w\d\.-]+)/$', 'graphs', name='oam_graphs'),
)
