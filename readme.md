# DSL Bandwidth Management Script

This script retrieves Downstream and Upstream attainable rates from a DSL modem
via SNMP, calculates proposed Queue Tree Max Limits for Mikrotik RouterOS,
and sets these limits. Configuration is loaded from a JSON file or environment
variables.

The max limit is calculated as a percentage of the current rate - in this case,
10% of headroom is allowed for to suit a CAKE/FQ-CODEL queue.

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Example crontab entry](#example-crontab-entry)
- [Example Log Output](#example-log-output)
- [Author](#author)
- [License](#license)

## Dependencies

- **pysnmp:** SNMP library for Python ([pysnmp](https://pypi.org/project/pysnmp/))
- **routeros_api:** MikroTik RouterOS API for Python ([routeros_api](https://github.com/BenMenking/routeros_api))

## Installation

1. Clone the repository:

    `git clone https://github.com/naturalnetworks/mtqosadj.git`

1. Create a Python Virtual Environment

    ```
    cd mtqosadj
    python3 -m venv .venv
    source .venv/bin/activate
    ```

1. Install dependencies:

    `pip install -r requirements.txt`
    
## Configuration

Edit `config.json` to set SNMP and RouterOS parameters. Alternatively, use environment
variables for sensitive information.

## Usage

Run the script with the necessary permissions to read SNMP information from the DSL modem
and set Queue Tree Max Limits on the MikroTik RouterOS.

`/path/to/python_app/.venv/bin/python3 /path/to/python_app/main.py`

## Example contab entry

`*/30 * * * * user /path/to/python_app/.venv/bin/python3 /path/to/python_app/main.py`

## Example log ouput

```INFO: DSL Downstream/Upstream actual rates: 50676736/10820608 bps (50676.74/10820.61 kbps)
INFO: Download/Upload Queue CURRENT Max Limit: 45609063/9738548
INFO: Setting Queue "download" Max Limit to 45609063
INFO: Setting Queue "upload" Max Limit to 9738548
INFO: Download/Uploads Queue APPLIED Max Limits: 45609063/9738548
```
