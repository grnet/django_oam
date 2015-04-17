# GRNET OAM SAMPLE APP.
This django application gets the vpn connections and applies oam configuration
to the routers in order to monitor the quality of the connection. Currently its
tailored to the GRNET NOCs network and the infrastructure so some functions which
use internal mechanisms, like databases and GRNET specific services are not
implemented in this app. Please note that this repository is a small guide to help you
set up oam on your network in an automated way, and to demostrate how GRNET does it, in order
to help/inspire/share knowledge.

## Requirements
Required dependencies for this app to work properly:
 - ncclient (`ncclient=0.4.3`)
 - lxml (`lxml=3.3.5`)
 - nxpy (`nxpy=0.4.1`) (https://code.grnet.gr/projects/nxpy/wiki/Wiki)
 - requests

## Installation
This app has been created and tested in django 1.4.5 (the django version for debian wheezy)

1. Add oam in the INSTALLED_APPS
3. include oam.urls file in your root url file.
4. Set a the required settings in settings.py file:

		NETCONF_USERNAME = 'user-ro'
		NETCONF_PASSWORD = 'pass'

		NETCONF_USERNAME_RW = 'user-rw'
		NETCONF_PASSWORD_RW = 'pass'
		ICINGA_SERVER = 'localhost'


	*Note that the user must have access to all the nodes.*

	Then we have to register the url at which the app will be serving the oam devices.

		OAM_NODES_HOST = 'https://example.com/oam'

5. edit `oam/management_commands/validate_config.py` and add the email address to which this command should send its reports. You can also add a setting for that.
6. create a cronjob which updates the rrds (`./manage.py update_oam_rrds`) every 4 minutes
7. create a cronjob which validates config
8. Create a cronjob which runs check_oam
9. Make sure cache is running and enter the cache config in settings.py

		CACHES = {
		    'default': {
		        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
		        'LOCATION': '127.0.0.1:11211',
		    }
		}

## Not implemented functions
This app is tailored for the services and infrastructure of GRNET.
In order to be reusable from anyone, we have removed the trivial parts and added
some documentation in order to help you how to do that properly.

The functions that use GRNETs infrastructure are:

- `utils.helper_functions.make_service_couples`
	Retrieves both ends of the pseudowire and returns a list with dictionaries
	as items. Each one of these dictionaries has two keys: `from` and `to`.
	Ideally, this function should return list of dicts like this one:

	    [{
	        'from': {
	            'node': 'host1.example.com',
	            'ifce': {
	                'name': 'ifce1',
	                 'description': 'some description'
	             }
	         }
	    },....]


- `utils.helper_functions.get_md`
	Returns the name of the maintenance domain, has an argument, the interface.
	Note that this should be unique for each vpn connection.

- `utils.helper_functions.get_ends`
	This is a trivial function that returns a dictionary with the connections
	each host has. It uses both previous functions and it heavilly depends on our
	infrastructure.

	Example conf dict:

	    {u'host1.grnet.gr':
	        [
	            {
	               'ma_mep': '52',
	               'ma_mep_auto_disco': True,
	               'ma_mep_dir': 'up',
	               'ma_mep_ifce': u'ge-1/1/1.0',
	               'ma_mip_hf': 'default',
	               'ma_name': 'vpn',
	               'ma_rem_mep': '51',
	               'md_level': '5',
	               'md_name': u'EXAMPLE_NAME',
	               'sla_iter_profiles': ['delay-measurement', 'loss-measurement']
	            }
	        ],
	    u'host2.grnet.gr':
	        [
	            {
	               'ma_mep': '52',
	               'ma_mep_auto_disco': True,
	               'ma_mep_dir': 'up',
	               'ma_mep_ifce': u'ge-1/1/1.0',
	               'ma_mip_hf': 'default',
	               'ma_name': 'vpn',
	               'ma_rem_mep': '51',
	               'md_level': '5',
	               'md_name': u'EXAMPLE_NAME2',
	               'sla_iter_profiles': ['delay-measurement', 'loss-measurement']
	            }
	        ]
	    }


## Management Commands
There are the following management commands:

- oam_nadjicingo, which gets all the hosts and the interfaces and creates passive check configuration
for icinga.

- check_oam, which connects via netconf to the routers, makes a query and gets their operational status.
Then it informs icinga about it.

- validate_config, which checks if the oam configuration applied to each routers agrees with the one
generated from the database.

- update_oam_rrds, which creates two rrds per connection, if they do not already exist, and updates them with the current values
it got from OAM service the corresponding device. These rrds are informed for the delay and jitter values each.

## Applying oam configuration
You can create, apply and update oam config by using the following command:

`./manage.py validate_config`

Validate config uses a dictionary with the state on which each host in the network should be
according to the vpns. Then it gets the current OAM configuration from each device and compares it with the previous dict.
Then if there are differences among these two (there should not be any, if the vpns have not changed),
then the new OAM configuration should be applied via netconf to the device. Finally a report of the changes on the network will be sent
to the addresses defined on `oam/management_commands/validate_config.py`.

## Icinga
The icinga configuration is generated with:

`./manage.py oam_nadgicingo`

the default behaviour is to generate a configuration without the hosts.
To add hosts one has to run:

`./manage.py oam_nadgicingo with-hosts`

### Icinga config.
There also is a url which generates the configuration. One can use it in case the icinga server
is on another device.

`/oam/icinga_config/` or `/oam/icinga_config/?with_hosts=true` in case the hosts are not already defined on icinga.
So a cronjob is needed to renew the config:

	curl https://<host>/oam/icinga_config/ > oam.cfg

and with hosts:

	curl https://<host>/oam/icinga_config/?with_hosts=true > oam.cfg

The configuration is created when the templates under `oam/templates/oam/` are rendered. You can change them to suit your needs.

Then, the OAM info can be pushed to icinga with:

`./manage.py check_oam` via nsca.

That means that icinga must be configured to have passive checks enabled and
an nsca server up and running.

## Creating the graphs

### Creating/Updating the rrds
`./manage.py update_oam_rrds` creates and updates the required rrds under `oam/rrd/` directory.

Then the graphs can be created dynamically by hitting:
`/<oam_url>/<device_name>/`
