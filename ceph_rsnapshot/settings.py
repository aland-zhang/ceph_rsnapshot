
import os
import sys
import tempfile

import yaml
import logging


# first one found in this list is the one used
DEFAULT_CONFIG_HIERARCHY = [
    'ceph_rsnapshot.yaml',
    '/home/ceph_rsnapshot/config/ceph_rsnapshot.yaml',
]

LOG_FORMAT = ("%(asctime)s [%(levelname)-5.5s] [%(name)s] %(message)s")

# allowed characters in settings strings here:
# alphanumeric, forward slash / and literal . and _ and -
# Note the - needs to be last in the re group
STRING_SAFE_CHAR_RE = "[a-zA-Z0-9/\._-]"

# some settings need extra characters allowed
ADDITIONAL_SAFE_CHARS = dict(
    SNAP_NAMING_DATE_FORMAT='%',
    SNAP_DATE=" ",
    EXTRA_ARGS=" ",
)


SETTINGS = dict(
    CEPH_HOST='localhost',
    CEPH_USER='admin',
    CEPH_CLUSTER='ceph',

    # POOLS is a comma separated list of pools to backup; can be a single pool
    POOLS='rbd',

    # NOTE: POOL singular is for internal use only,
    # it will be overwritten if specified. Use POOLS above
    POOL='',

    # path on the ceph node to use for the temporary export of qcows
    # if it does not exist, the script will create it and intervening dirs
    # also this script will create subdirectories for each pool
    # and will chmod those pool directories 700
    QCOW_TEMP_PATH='/tmp/qcows',

    # prefix for temp dir to store temporary rsnapshot conf files
    TEMP_CONF_DIR_PREFIX='ceph_rsnapshot_temp_conf_',

    # ...or can override and set whole dir
    # this script will create this directory if it does not exist
    TEMP_CONF_DIR='',

    # whether to keep temp rsnap config files
    # note if temp_conf_dir is specified, and keepconf is not specified,
    # then this script will set keepconf true
    KEEPCONF=False,

    # base path on this node for backup qcows to land
    # this script will chmod the final directory of it 700
    # also if it does not exist, the script will create it
    # and any intervening directories also 700
    BACKUP_BASE_PATH='/backups/ceph_rsnapshot',

    # base path for logs, and also rsnapshot logs
    # this script will chmod the final directory of it 700
    # also if it does not exist, the script will create it
    # and any intervening directories also 700
    LOG_BASE_PATH='/home/ceph_rsnapshot/logs',
    LOG_FILENAME='ceph_rsnapshot.log',

    # file to write out nagios readable status output at the end of each run
    STATUS_FILENAME='ceph_rsnapshot.status',

    # TODO allow specifying alt path to a jinja template
    # TEMPLATE = '',
    VERBOSE=False,

    # noop means don't make any changes to the system - no log dirs, no backup
    # dirs, no actual exporting of qcows, etc. Logging goes to stdout only,
    # this includes dumps of the rsnap config files
    NOOP=False,

    # set this to true to suppress rotating orphans. useful if testing a backup
    # on an artificially restrictive image_re and don't want to cycle the other
    # backups
    NO_ROTATE_ORPHANS=False,

    # IMAGE_RE - an RE to filter ceph rbd images to back up
    # opennebula images are one-NN
    # vms are one-NN-XX-YY for image NN vm XX and disk YY
    # images or vms are (with the additional accidental acceptance of one-NN-XX
    IMAGE_RE=r'^one(-[0-9]+){1,3}$',

    # rsnapshot parameters
    RETAIN_INTERVAL='daily',
    RETAIN_NUMBER=14,
    # extra arguments to pass to rsnapshot
    EXTRA_ARGS='',

    # date format string to pass to `date` to get ceph snapshot naming,
    # iso format %Y-%m-%d would yield names like imagename@2016-07-18
    # match this to what your external ceph snapshot creation script is using
    SNAP_NAMING_DATE_FORMAT='%Y-%m-%d',

    # string argument to pass to `date --date "<string>"` to generate snap name
    # to back up. examples "today" or "1 day ago"
    SNAP_DATE="today",
    # FIXME - convert to also use a 2nd parameter called SNAP_NAME for after
    # date has been converted to a string

    # alternatively, check a status file on the ceph host to see when the snaps
    # are ready - will check for files where the name of the file is the snap
    # name to use
    # example - write out YYYY-MM-DD when the snapshots are done
    USE_SNAP_STATUS_FILE=False,
    SNAP_STATUS_FILE_PATH="/var/spool/ceph-snapshot",

    # min free bytes to leave on ceph node for exporting qcow temporarily
    MIN_FREESPACE=5 * 1024 * 1024 * 1024,  # 5GB

    # enable for extra logging for sh calls
    SH_LOGGING=False,
)


def setup_stdout_logger(level=logging.INFO):
    """ setup a basic stdout-only logger
    """
    logger = logging.getLogger('ceph_rsnapshot_bootstrap')
    logger.setLevel(level)
    logFormatter = logging.Formatter(LOG_FORMAT)
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    return logger



def load_settings(config_file=''):
    logger = setup_stdout_logger()
    if config_file == '':
        for conf_file in DEFAULT_CONFIG_HIERARCHY:
            if os.path.isfile(conf_file):
                config_file = conf_file
                break
    # FIXME no logging here yet because we haven't loaded logging yet
    logger.debug('using settings file %s' % config_file)
    settings = SETTINGS.copy()
    user_did_provide_keepconf = False
    if os.path.isfile(config_file):
        with open(config_file) as f:
            cfg = yaml.load(f.read()) or {}
        for setting in cfg:
            if setting.upper() not in SETTINGS:
                logger.error('ERROR: unsupported setting %s\n' % setting)
                sys.exit(1)
            else:
                if setting.upper() == 'KEEPCONF':
                    # check for this here, because if we've been passed a conf
                    # dir, and keepconf is not specified, then we'll set
                    # KEEPCONF. otherwise, we'll let user config stand as-is
                    user_did_provide_keepconf = True
                settings[setting.upper()] = cfg[setting]
    else:
        logger.debug('no config file found - using default settings')
    if settings['TEMP_CONF_DIR'] and not user_did_provide_keepconf:
        settings['KEEPCONF'] = True
    globals().update(settings)
    return settings
