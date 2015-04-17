import nxpy as np
from ncclient import manager
from lxml import etree as ET
import socket
import time
from django.conf import settings


class Retriever(object):
    def __init__(self, host, xml=None):
        self.xml = xml
        self.host = host

    def fetch_xml(self):
        with manager.connect(host=self.host, username=settings.NETCONF_USERNAME, password=settings.NETCONF_PASSWORD, hostkey_verify=False, port=22, device_params={"name": "junos"}) as m:
            xmlconfig = m.get_config(source='running').data_xml
            self.xml = xmlconfig
        return xmlconfig

    def proccess_xml(self):
        if self.xml:
            xmlconfig = self.xml
        else:
            xmlconfig = self.fetch_xml()
        parser = np.Parser()
        parser.confile = xmlconfig
        device = parser.export()
        return device

    def fetch_device(self):
        device = self.proccess_xml()
        return device


class Applier(object):
    def __init__(self, md=None, device=None):
        '''
        eg. md = [{'md_name':'DUTH_EIE...', 'md_level':'5', 'ma_name': 'vpn',
                    'ma_mep': '52', 'ma_mep_ifce':'ge-0/1', 'ma_mip_hf': 'default',
                    'ma_mep_dir': 'up', 'ma_mep_auto_disco': True,
                        'ma_rem_mep': '51', 'sla_iter_profiles': ['etet', 'dadad']
                   }, ....
                   ]

        '''
        self.md = md
        self.device = device

    def to_xml(self, operation='replace', maintenance_domains_to_delete=[]):
        if self.md:
            md = self.md
            eo = np.EthernetOAMCFM()
            for md_to_delete in maintenance_domains_to_delete:
                # must delete these maintenance domains
                cfmmd = np.CFMMD()
                cfmmd.name = md_to_delete
                cfmmd.operation = 'delete'
                eo.maintenance_domains.append(cfmmd)
            for maintdom in md:
                cfmmd = np.CFMMD()
                cfmmd.name = maintdom['md_name']
                cfmmd.operation = operation
                cfmmd.level = maintdom['md_level']
                if maintdom.get('sla_iter_profiles') is not None:
                    ma = np.MaintenanceAssoc(
                        name=maintdom['ma_name'],
                        mep_name=maintdom['ma_mep'],
                        mep_ifce=maintdom['ma_mep_ifce'],
                        mip_hf=maintdom['ma_mip_hf'],
                        mep_direction=maintdom['ma_mep_dir'],
                        mep_auto_disco=maintdom['ma_mep_auto_disco'],
                        mep_rem_name=maintdom['ma_rem_mep'],
                        sla_iter_profiles=maintdom.get('sla_iter_profiles')
                    )
                else:
                    ma = np.MaintenanceAssoc(
                        name=maintdom['ma_name'],
                        mep_name=maintdom['ma_mep'],
                        mep_ifce=maintdom['ma_mep_ifce'],
                        mip_hf=maintdom['ma_mip_hf'],
                        mep_direction=maintdom['ma_mep_dir'],
                        mep_auto_disco=maintdom['ma_mep_auto_disco'],
                        mep_rem_name=maintdom['ma_rem_mep']
                    )
                ma.operation
                cfmmd.maintenance_association = ma
                eo.maintenance_domains.append(cfmmd)
            eoam = np.EthernetOAM()
            eoam.connectivity_fault_management = eo
            oam = np.OAM()
            oam.ethernet = eoam
            device = np.Device()
            device.protocols['oam'] = oam
            d = device.export(netconf_config=True)
            return ET.tostring(d)
        else:
            return False

    def debug_apply(self, operation='replace', md=[]):
        from helper_functions import is_successful
        reason = None
        # delete the following maintenance domains
        configuration = self.to_xml(operation=operation, maintenance_domains_to_delete=md)
        edit_is_successful = False
        host = socket.gethostbyname(self.device)
        if configuration:
            with manager.connect(host=host, username=settings.NETCONF_USERNAME_RW, password=settings.NETCONF_PASSWORD_RW, hostkey_verify=False, port=22, device_params={"name": "junos"}) as m:
                assert(":candidate" in m.server_capabilities)
                try:
                    edit_response = m.edit_config(target='candidate', config=configuration, test_option='test-then-set')
                    edit_is_successful, reason = is_successful(edit_response.tostring)
                except Exception as e:
                    m.discard_changes()
                    return False, e
        print 'edited config'

    def apply(self, operation='replace', md=False):
        from helper_functions import is_successful
        reason = None
        if md:
            configuration = self.to_xml(operation=operation, maintenance_domains_to_delete=md)
        else:
            configuration = self.to_xml(operation=operation)
        edit_is_successful = False
        commit_confirmed_is_successful = False
        commit_is_successful = False
        host = socket.gethostbyname(self.device)
        if configuration:
            with manager.connect(host=host, username=settings.NETCONF_USERNAME_RW, password=settings.NETCONF_PASSWORD_RW, hostkey_verify=False, port=22, device_params={"name": "junos"}) as m:
                assert(":candidate" in m.server_capabilities)
                try:
                    edit_response = m.edit_config(target='candidate', config=configuration, test_option='test-then-set')
                    print edit_response.tostring
                    edit_is_successful, reason = is_successful(edit_response.tostring)
                except Exception as e:
                    m.discard_changes()
                    return False, e
                if edit_is_successful:
                    try:
                        commit_confirmed_response = m.commit(confirmed=True, timeout="180")
                        time.sleep(65)
                        commit_confirmed_is_successful, reason = is_successful(commit_confirmed_response.tostring)
                        if not commit_confirmed_is_successful:
                            print 'Oops'
                            raise Exception()
                        else:
                            print "Successfully confirmed committed @ %s" % self.device
                    except Exception as e:
                        cause = "Caught commit confirmed exception: %s %s" % (e, reason)
                        cause = cause.replace('\n', '')
                        print cause
                        return False, cause
                    if edit_is_successful and commit_confirmed_is_successful:
                        try:
                            commit_response = m.commit(confirmed=False)
                            commit_is_successful, reason = is_successful(commit_response.tostring)
                            print "Successfully committed @ %s" % self.device
                            if not commit_is_successful:
                                raise Exception()
                            else:
                                return True, "Successfully committed"
                        except Exception as e:
                            cause = "Caught commit exception: %s %s" % (e, reason)
                            cause = cause.replace('\n', '')
                            print cause
                            return False, cause


# https://github.com/hughdbrown/dictdiffer
class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])
