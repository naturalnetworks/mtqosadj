#!/usr/bin/env python3
"""
DSL Bandwidth Management Script

This script retrieves Downstream and Upstream attainable rates from a DSL modem
via SNMP, calculates proposed Queue Tree Max Limits for Mikrotik RouterOS,
and sets these limits. Configuration is loaded from a JSON file or environment
variables.

The max limit is calculated as a percentage of the current rate - in this case
10% of headroom is allowed for to suit a CAKE/FQ-CODEL queue.

:Author: Ben Johns
:Version: 0.0.1
:License: MIT

**Dependencies:**
  - **pysnmp:** SNMP library for Python (`pysnmp <https://pypi.org/project/pysnmp/>`_)
  - **routeros_api:** MikroTik RouterOS API for Python (`routeros_api <https://github.com/BenMenking/routeros_api>`_)

**GitHub Repository:**
  - :github:`naturalnetworks/mtqosadj`

**Usage:**
Run the script with the necessary permissions to read SNMP information from the DSL modem
and set Queue Tree Max Limits on the MikroTik RouterOS.

**Configuration:**
Edit 'config.json' to set SNMP and RouterOS parameters. Alternatively, use environment
variables for sensitive information.

**Example crontab entry:**

*/30 * * * * user /path/to/python_app/.venv/bin/python3 /path/to/python_app/main.py

**Example Log Output:**
INFO: DSL Downstream/Upstream actual rates: 50676736/10820608 bps (50676.74/10820.61 kbps)
INFO: Download/Upload Queue CURRENT Max Limit: 45609063/9738548
INFO: Setting Queue "download" Max Limit to 45609063
INFO: Setting Queue "upload" Max Limit to 9738548
INFO: Download/Uploads Queue APPLIED Max Limits: 45609063/9738548 (45609.06/9738.55 kbps)

"""

__author__ = "Ben Johns"
__version__ = "0.0.1"
__license__ = "MIT"


# Import system modules
import argparse
import os
import logging
import json

# Import 3rd party modules
from pysnmp.hlapi import (
    getCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity
)
from routeros_api import RouterOsApiPool

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
)

# Function to read configuration from file
def read_config():
    with open('config.json', 'r', encoding='utf-8') as config_file:
        configuration = json.load(config_file)
    return configuration


# Function to convert bits per second to kilobits per second
def bits_to_kbps(bits_per_second):
    return round(bits_per_second / 1000, 2)

# Function to subtract a percentage from a number
def subtract_percentage(number, percentage):
    amount_to_subtract = number * (percentage / 100)
    result = number - amount_to_subtract
    return result

# Function to perform SNMP get request
def snmp_get(dsl_modem_ip, community_string, oid):
    snmp_request = getCmd(
        SnmpEngine(),
        CommunityData(community_string),
        UdpTransportTarget((dsl_modem_ip, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    
    error_indication, error_status, error_index, var_binds = next(snmp_request)
    
    if error_indication:
        print(f"SNMP Error: {error_indication}")
    else:
        return var_binds[0][1]

def get_queue_tree_attributes(api, queue_name):
    # Get the specific queue by name
    target_queue = api.get_resource('/queue/tree').get(name=queue_name)

    # Check if the queue tree entry exists
    if target_queue:
        queue_id = target_queue[0].get('id')
        max_limit_value = target_queue[0].get('max-limit')

        return queue_id, max_limit_value
    else:
        return None, None

def set_queue_tree_max_limit(api, queue_name, max_limit):
    # Get the specific queue by name
    target_queue = api.get_resource('/queue/tree').get(name=queue_name)

    # Check if the queue tree entry exists
    if target_queue:
        queue_id = target_queue[0].get('id')

    # Set Queue Tree Element
    if queue_id and max_limit:
        logging.info("Setting Queue \"%s\" Max Limit to %s", queue_name, max_limit)
        # queue_tree.set(id=str(queue_id), max_limit=str(max_limit))
        return
    else:
        logging.error("Queue ID or Max Limit is not set")
        return

def main(args):
    """ Main entry point of the app """

    # Load configuration
    config = read_config()

    # RouterOS Configuration
    ROUTER_IP = os.getenv('ROUTER_IP', config['routeros']['router_ip'])
    ROUTER_PORT = os.getenv('ROUTER_PORT',config['routeros']['router_port'])
    DOWNLOAD_QUEUE_NAME = os.getenv('DOWNLOAD_QUEUE_NAME', config['routeros']['download_queue_name'])
    UPLOAD_QUEUE_NAME = os.getenv('UPLOAD_QUEUE_NAME', config['routeros']['upload_queue_name'])
    USERNAME = os.getenv('ROUTER_USERNAME', config['routeros']['username'])
    PASSWORD = os.getenv('ROUTER_PASSWORD', config['routeros']['password'])

        # Create an API connection pool
    api_pool = RouterOsApiPool(
            ROUTER_IP,
            port=int(ROUTER_PORT),
            username=USERNAME,
            password=PASSWORD,
            plaintext_login=True,
            use_ssl=True,
            ssl_verify=False,
            ssl_verify_hostname=False
            )

    # Get an API connection from the pool
    api = api_pool.get_api()

    # SNMP Configuration
    DSL_MODEM_IP = os.getenv('DSL_MODEM_IP', config['snmp']['dsl_modem_ip'])
    SNMP_COMMUNITY_STRING = os.getenv('SNMP_COMMUNITY_STRING', config['snmp']['community_string'])
    SNMP_OID_DOWNSTREAM = os.getenv('SNMP_OID_DOWNSTREAM', config['snmp']['snmp_oid_downstream'])
    SNMP_OID_UPSTREAM = os.getenv('SNMP_OID_UPSTREAM', config['snmp']['snmp_oid_upstream'])

    # Retrieve and display downstream attainable rate
    try:
        dsl_downstream_act_rate = snmp_get(DSL_MODEM_IP, SNMP_COMMUNITY_STRING, SNMP_OID_DOWNSTREAM)
        dsl_upstream_act_rate = snmp_get(DSL_MODEM_IP, SNMP_COMMUNITY_STRING, SNMP_OID_UPSTREAM)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

    if dsl_downstream_act_rate is None or dsl_downstream_act_rate <= 0:
        logging.error("Error: Downstream attainable rate not found")
        exit(1)

    if dsl_upstream_act_rate is None or dsl_upstream_act_rate <= 0:
        logging.error("Error: Upstream attainable rate not found")
        exit(1)

    # Display results
    logging.info("DSL Downstream/Upstream actual rates: %s/%s bps (%s/%s kbps)",
            dsl_downstream_act_rate,
            dsl_upstream_act_rate,
            bits_to_kbps(dsl_downstream_act_rate),
            bits_to_kbps(dsl_upstream_act_rate)
            )
 
    # Set up the queue tree max limits based upon the actual rates, minus 10% for overhead
    mt_down_queue_set_max_limit = subtract_percentage(dsl_downstream_act_rate, 10)
    mt_up_queue_set_max_limit = subtract_percentage(dsl_upstream_act_rate, 10)
    
    logging.debug("Down/Up Queue Proposed Max Limits: %s/%s",
            mt_down_queue_set_max_limit,
            mt_up_queue_set_max_limit
            )

    mt_queue_tree_download_id, mt_queue_tree_download_max_limit_value = get_queue_tree_attributes(api, DOWNLOAD_QUEUE_NAME)
    mt_queue_tree_upload_id, mt_queue_tree_upload_max_limit_value = get_queue_tree_attributes(api, UPLOAD_QUEUE_NAME)

    if mt_queue_tree_download_id is not None and mt_queue_tree_upload_id is not None:
        logging.debug("Download/Upload Queue IDs: %s/%s", mt_queue_tree_download_id, mt_queue_tree_upload_id)

        logging.info("Download/Upload Queue CURRENT Max Limit: %s/%s",
            mt_queue_tree_download_max_limit_value,
            mt_queue_tree_upload_max_limit_value
            )
    else:
        logging.warning("Queue Tree entry not found.")

    # Set Download Queue
    set_queue_tree_max_limit(api, DOWNLOAD_QUEUE_NAME, mt_down_queue_set_max_limit)

    # Set Upload Queue
    set_queue_tree_max_limit(api, UPLOAD_QUEUE_NAME, mt_up_queue_set_max_limit)

    # Display results

    mt_queue_tree_download_applied_max_limit_value = int(get_queue_tree_attributes(api, DOWNLOAD_QUEUE_NAME)[1])
    mt_queue_tree_upload_applied_max_limit_value = int(get_queue_tree_attributes(api, UPLOAD_QUEUE_NAME)[1])

    if mt_queue_tree_download_applied_max_limit_value is not None and mt_queue_tree_upload_applied_max_limit_value is not None:
        logging.info("Download/Uploads Queue APPLIED Max Limits: %s/%s (%s/%s kbps)",
            mt_queue_tree_download_applied_max_limit_value,
            mt_queue_tree_upload_applied_max_limit_value,
            bits_to_kbps(mt_queue_tree_download_applied_max_limit_value),
            bits_to_kbps(mt_queue_tree_upload_applied_max_limit_value)
            )
    else:
        logging.warning("Queue Tree entry not found.")

    api_pool.disconnect()


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()
    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))
    args = parser.parse_args()
    main(args)