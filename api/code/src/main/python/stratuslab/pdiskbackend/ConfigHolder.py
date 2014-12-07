import StringIO
import ConfigParser
from ConfigParser import NoOptionError, NoSectionError

from stratuslab.pdiskbackend.defaults import CONFIG_DEFAULTS, CONFIG_MAIN_SECTION, \
    CONFIG_FILE_NAME, VERBOSITY
from stratuslab.pdiskbackend.utils import abort


class ConfigHolder(object):

    def __init__(self, config_file_name=CONFIG_FILE_NAME, verbosity=VERBOSITY):
        self._config = self._read_configuration(config_file_name)
        self.verbosity = verbosity

    def get(self, section, param):
        return self._config.get(section, param)

    def _read_configuration(self, config_file):
        """Read configuration file. The file must exists as there is no
        sensible default value for several options.
        """
        config = ConfigParser.ConfigParser()
        self._read_configuration_defaults(config)
        self._read_configuration_from_file(config, config_file)
        return config

    def _read_configuration_defaults(self, config):
        config.readfp(StringIO.StringIO(CONFIG_DEFAULTS))

    def _read_configuration_from_file(self, config, config_file):
        try:
            config.readfp(open(config_file))
        except IOError as (errno, errmsg):
            if errno == 2:
                abort('Configuration file (%s) is missing.' % config_file)
            else:
                abort('Error opening configuration file (%s): %s (errno=%s)' %
                      (config_file, errmsg, errno))

    def set_backend_proxy_attributes(self, backend_attributes, proxy_name):
        self._set_backend_proxy_specific_attributes(backend_attributes, proxy_name)
        backend_attributes['mgt_user_name'], backend_attributes['mgt_user_private_key'] = \
            self._get_mgt_info_from_config(proxy_name)

    def get_proxy_name(self):
        """Return first proxy name from the comma separated list."""
        return self.get_proxy_names()[0]

    def get_proxy_names(self):
        """Return all proxy names as list from the comma separated list."""
        try:
            return self._config.get(CONFIG_MAIN_SECTION,
                                    'iscsi_proxies').split(',')
        except ValueError:
            abort("Invalid value specified for 'iscsi_proxies' "
                  "(section %s) (must be a comma-separated list)" %
                  CONFIG_MAIN_SECTION)

    def get_backend_type(self, proxy_name):
        try:
            return self._config.get(proxy_name, 'type')
        except:
            abort("Section '%s' or required attribute 'type' missing" %
                  (proxy_name))

    def _set_backend_proxy_specific_attributes(self, backend_attributes, proxy_name):
        try:
            for attribute in backend_attributes.keys():
                backend_attributes[attribute] = self._config.get(proxy_name,
                                                                 attribute)
        except NoOptionError:
            abort("Required option '%s' is missing in section '%s'." %
                  (attribute, proxy_name))
        except NoSectionError:
            abort("Section '%s' is missing in configuration" % proxy_name)

    def _get_mgt_info_from_config(self, backend_section):
        """Return a tuple with the appropriated management information."""

        mgt_user_name = None
        mgt_user_private_key = None
        if backend_section != 'local':
            try:
                mgt_user_name = self._config.get(backend_section,
                                                 'mgt_user_name')
            except:
                try:
                    mgt_user_name = self._config.get(CONFIG_MAIN_SECTION,
                                                     'mgt_user_name')
                except:
                    abort('Undefined user name to connect to the proxy.')
            try:
                mgt_user_private_key = self._config.get(backend_section,
                                                        'mgt_user_private_key')
            except:
                try:
                    mgt_user_private_key = self._config.get(CONFIG_MAIN_SECTION,
                                                            'mgt_user_private_key')
                except:
                    abort('Undefined SSH private key to connect to the proxy.')

        return mgt_user_name, mgt_user_private_key
