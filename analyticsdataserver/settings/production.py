"""Production settings and globals."""



from os import environ

import django
import six
import yaml
# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured

from analyticsdataserver.settings.base import *
from analyticsdataserver.settings.logger import get_logger_config

LOGGING = get_logger_config()

def get_env_setting(setting):
    """Get the environment setting or return exception."""
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = ['*']
########## END HOST CONFIGURATION

CONFIG_FILE=get_env_setting('ANALYTICS_API_CFG')

with open(CONFIG_FILE) as f:
  config_from_yaml = yaml.load(f, Loader=yaml.FullLoader)

REPORT_DOWNLOAD_BACKEND = config_from_yaml.pop('REPORT_DOWNLOAD_BACKEND', {})

JWT_AUTH_CONFIG = config_from_yaml.pop('JWT_AUTH', {})
JWT_AUTH.update(JWT_AUTH_CONFIG)

vars().update(config_from_yaml)
vars().update(REPORT_DOWNLOAD_BACKEND)

DB_OVERRIDES = dict(
    PASSWORD=environ.get('DB_MIGRATION_PASS', DATABASES['default']['PASSWORD']),
    ENGINE=environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    USER=environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    NAME=environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    HOST=environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    PORT=environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
)

for override, value in DB_OVERRIDES.items():
    DATABASES['default'][override] = value
