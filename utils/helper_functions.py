from django.core.cache import cache
from classes import Applier, Retriever, DictDiffer
from lxml import etree as ET


def create_configuration_dict(
    md_name,
    ma_mep_ifce,
    ma_mep,
    ma_rem_mep,
    md_level='5',
    ma_name='vpn',
    ma_mip_hf='default',
    ma_mep_dir='up',
    ma_mep_auto_disco=True,
    sla_iter_profiles=['delay-measurement', 'loss-measurement']
):
    conf = {
        'md_name': md_name,
        'md_level': md_level,
        'ma_name': ma_name,
        'ma_mep_ifce': ma_mep_ifce,
        'ma_mip_hf': ma_mip_hf,
        'ma_mep': ma_mep,
        'ma_mep_dir': ma_mep_dir,
        'ma_mep_auto_disco': ma_mep_auto_disco,
        'ma_rem_mep': ma_rem_mep,
    }
    if sla_iter_profiles is not None:
        conf.update({'sla_iter_profiles': sla_iter_profiles})
    return conf


def get_md(ifce):
    raise NotImplementedError('Return a string that represents the maintenance domain')
    # E.G.
    # return '_'.join(
    #     ifce['description']
    # )
    # note that this should be unique for each connection


def get_ends():
    conf_dict = cache.get('vpn_ends')
    if not conf_dict:
        conf_dict = {}
        # get a list of pseudowire couples
        pws = make_service_couples()
        # Lets iterate between the values
        # this is an untested example which supposes that we have a list
        # of dictionaries consisted of the keys `from` and `to`
        # which contain other dictionaries with the keys `node` and `ifce`
        # for example:
        # {
        #     'from': {
        #         'node': 'host1.example.com',
        #         'ifce': {
        #             'name': 'ifce1',
        #             'description': 'some description'
        #         }
        #     }
        # }
        # this is an example
        for vpn in pws:
            fromnode = vpn['from']['node']['name']
            tonode = vpn['to']['node']['name']
            frommep = 51  # we set the values we want
            tomep = 52
            md = get_md(vpn['from']['node']['ifce'])
            if fromnode not in conf_dict:
                conf_dict[fromnode] = []
            if tonode not in conf_dict:
                conf_dict[tonode] = []
            # if not vlan then oam config cannot be applied,
            # the traffic is untagged
            # ignore ae interfaces (oam cannot be applied properly)
            if vpn['from']['ifce']['name'][:2] == 'ae' and vpn['from']['ifce']['name'].split('.')[-1] == '0':
                continue
            if vpn['to']['ifce']['name'][:2] == 'ae' and vpn['to']['ifce']['name'].split('.')[-1] == '0':
                continue
            conf_dict[fromnode].append(
                create_configuration_dict(
                    md_name=md,
                    ma_mep_ifce=vpn['from']['ifce']['name'],
                    ma_mep=str(frommep),
                    ma_rem_mep=str(tomep)
                )
            )
            conf_dict[tonode].append(
                create_configuration_dict(
                    md_name=md,
                    ma_mep_ifce=vpn['to']['ifce']['name'],
                    ma_mep=str(tomep),
                    ma_rem_mep=str(frommep)
                )
            )
        # just add it to the cache to avoid discovering the same vpns
        # over and over again
        cache.set('vpn_ends', conf_dict, 43200)
    raise NotImplementedError('This function should be altered as well in order to return the right data.')
    # Example conf dict:
    # {u'host1.grnet.gr':
    #     [
    #         {
    #            'ma_mep': '52',
    #            'ma_mep_auto_disco': True,
    #            'ma_mep_dir': 'up',
    #            'ma_mep_ifce': u'ge-1/1/1.0',
    #            'ma_mip_hf': 'default',
    #            'ma_name': 'vpn',
    #            'ma_rem_mep': '51',
    #            'md_level': '5',
    #            'md_name': u'EXAMPLE_NAME',
    #            'sla_iter_profiles': ['delay-measurement', 'loss-measurement']
    #         }
    #     ],
    # u'host2.grnet.gr':
    #     [
    #         {
    #            'ma_mep': '52',
    #            'ma_mep_auto_disco': True,
    #            'ma_mep_dir': 'up',
    #            'ma_mep_ifce': u'ge-1/1/1.0',
    #            'ma_mip_hf': 'default',
    #            'ma_name': 'vpn',
    #            'ma_rem_mep': '51',
    #            'md_level': '5',
    #            'md_name': u'EXAMPLE_NAME2',
    #            'sla_iter_profiles': ['delay-measurement', 'loss-measurement']
    #         }
    #     ]
    # }
    return conf_dict


def get_ends_builder():
    applier_cfg = {}
    conf_dict = get_ends()
    for k in conf_dict.keys():
        applier_cfg[k] = Applier(md=conf_dict[k], device=k)
    return applier_cfg


def make_service_couples():
    couples_list = []
    raise NotImplementedError('Create a list of all the vpns, with dicts containing the ends.')
    # pws = A list of all the pseudowires.
    # for pw in pws:
    #     couples_list.append({"from": pw, "to": pw.other_side})

    # The result should look like this:
    # [{'from': <Pseudowire: (202):point1.grnet.gr<->point2.grnet.gr>,
    # 'to': <Pseudowire: (202):point2.grnet.gr<->point1.grnet.gr>},
    # {'from': <Pseudowire: (245):point3.grnet.gr<->point4.grnet.gr>,
    # 'to': <Pseudowire: (245):point4.grnet.gr<->point3.grnet.gr>}]

    # Obviously, we (GRNET) use the database in order to retrive the
    # pseudowires, thats why the list contains "Pseudowire" objects.

    # Ideally, someone could create a list of dicts like this one:
    # [{
    #     'from': {
    #         'node': 'host1.example.com',
    #         'ifce': {
    #             'name': 'ifce1',
    #             'description': 'some description'
    #         }
    #     }
    # },....]
    return couples_list


def is_successful(response):
    from StringIO import StringIO
    doc = parsexml_(StringIO(response))
    rootNode = doc.getroot()
    success_list = rootNode.xpath("//*[local-name()='ok']")
    if len(success_list) > 0:
        return True, None
    else:
        reason_return = ''
        reason_list = rootNode.xpath("//*[local-name()='error-message']")
        for reason in reason_list:
            reason_return = "%s %s" % (reason_return, reason.text)
        return False, reason_return


def parsexml_(*args, **kwargs):
    if 'parser' not in kwargs:
        kwargs['parser'] = ET.ETCompatXMLParser()
    doc = ET.parse(*args, **kwargs)
    return doc


def candidate_config(node_name):
    devices = get_ends_builder()
    # this is an Applier instance
    return devices[node_name].md


def get_config(node_name):
    full_config = []
    r = Retriever(host=node_name)
    config = r.fetch_device()
    mds = config.protocols['oam'].ethernet.connectivity_fault_management.maintenance_domains
    for md in mds:
        ma = md.maintenance_association
        try:
            full_config.append(
                create_configuration_dict(
                    md_name=md.name,
                    ma_mep_ifce=ma.mep['ifce'],
                    ma_mep=ma.mep['name'],
                    ma_rem_mep=ma.mep['remote_mep']['name'],
                    md_level=md.level,
                    ma_name=ma.name,
                    ma_mip_hf=ma.mip_half_function,
                    ma_mep_dir=ma.mep['direction'],
                    ma_mep_auto_disco=ma.mep['auto_discovery'],
                    sla_iter_profiles=ma.mep['remote_mep']['sla_iterator_profiles']
                )
            )
        except Exception as e:
            print 'Caught exception %s.' % e
    return full_config


def valid_md(md):
    if ':' in md and '_' in md:
        try:
            int(md.split('_')[-1])
        except TypeError:
            return False
        return True
    return False


def diff(node_name):
    current = get_config(node_name)
    db = candidate_config(node_name)
    apply_config = False
    message = ''
    maintenance_domains = []
    okay = True
    if current != db:
        for c in range(len(current)):
            try:
                cur = current[c]
            except IndexError:
                # print 'No oam config currently on %s for %s' % (node_name, db[c].get('ma_mep_ifce'))
                apply_config = True
            for db_entry in db:
                d = None
                if db_entry.get('ma_mep_ifce') == cur.get('ma_mep_ifce'):
                    d = db_entry
                    break
            if not d:
                maintenance_domain = cur.get('md_name')
                # we have to reproduce the md according to the
                # ifces, by using get_md(ifce).
                if valid_md(maintenance_domain):
                    maintenance_domains.append(maintenance_domain)
                else:
                    message += '\nNo valid VPN found for %s on %s at %s' % (maintenance_domain, cur.get('ma_mep_ifce'), node_name)
                continue
            diff = DictDiffer(cur, d)
            message_header = ''
            debug_message = ''
            if (diff.added() or diff.changed() or diff.removed()) and not ('ma_rem_mep' == diff.changed().pop() and len(diff.changed()) == 1):
                message_header += '\nThe oam configuration is not in the state is was supposed to be in %s %s, %s ' % (node_name, cur.get('ma_mep_ifce'), cur.get('md_name'))
                if diff.added():
                    for a in diff.added():
                        if cur.get(a):
                            debug_message += '+ %s' % cur.get(a)
                        if d.get(a):
                            debug_message += '+ %s in db' % cur.get(a)
                if diff.removed():
                    for a in diff.removed():
                        if d.get(a):
                            debug_message += '- %s in db' % d[a]
                        if cur.get(a):
                            debug_message += '- %s' % cur.get(a)
                if diff.changed():
                    for a in diff.changed():
                        if a != 'ma_rem_mep':
                            debug_message += 'changed: \n%s: %s in db \n%s: %s in current' % (a, d.get(a), a, cur.get(a))
                            # if the maintenance domain has changed, we have to delete the old one and apply the new name for
                            # the interface.
                            if a == 'md_name':
                                maintenance_domains.append(cur.get('md_name'))
                if debug_message:
                    message += message_header
                    message += debug_message
            if not message and not maintenance_domains and not apply_config:
                okay = True
            else:
                okay = False
    if okay:
        return {
            'ok': okay
        }
    else:
        return {
            'ok': okay,
            'apply': apply_config,
            'message': message,
            'maintenance_domains': maintenance_domains,
        }


def diff_carrier():
    devices = get_ends_builder()
    nodes = devices.keys()
    message = ''
    for node in nodes:
        try:
            actions = diff(node)
        except Exception as e:
            print 'could not connect to %s: %s' % (node, e)
        finally:
            if not actions.get('ok'):
                if actions.get('message') != '':
                    message += '\n%s' % (actions.get('message'))
                if actions.get('apply'):
                    message += '\nApplying oam config on %s ' % node
                    devices[node].apply()
                if actions.get('maintenance_domains'):
                    for md in actions.get('maintenance_domains'):
                        message += '\nDeleting %s and Reapplying config on %s' % (md, node)
                    devices[node].apply(md=actions.get('maintenance_domains'))
    if not message:
        message = 'Oam run succesfully. Nothing to report'
    return message


def get_carrier():
    return get_ends().keys()
