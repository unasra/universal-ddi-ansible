#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Infoblox Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ipam_next_available_address_block_info
short_description: Manage NextAvailableAddressBlock
description:
    - Manage NextAvailableAddressBlock
version_added: 2.0.0
author: Infoblox Inc. (@infobloxopen)
options:
    id:
        description:
            - ID of the object
        type: str
        required: true
    cidr:
        description:
            - The CIDR value of the object
        type: int
        required: true
    count:
        description:
            - Number of objects to generate. Default 1 if not set
        type: int
        required: false
extends_documentation_fragment:
    - infoblox.universal_ddi.common
"""  # noqa: E501

EXAMPLES = r"""
    - name: "Create an Address Block"
      infoblox.universal_ddi.ipam_address_block:
        address: "10.0.0.0/16"
        space: "{{ ip_space.id }}"
        state: "present"

    - name: Get Next Available Address Block Information by ID
      infoblox.universal_ddi.ipam_next_available_address_block_info:
          id: "{{ address_block.id }}"
          cidr: 20

    - name: Get Next Available Address Block Information by ID and Count
      infoblox.universal_ddi.ipam_next_available_address_block_info:
        id: "{{ address_block.id }}"
        cidr: 24
        count: 5
"""

RETURN = r"""
id:
    description:
        - ID of the AddressBlock object.
    type: str
    returned: Always
objects:
    description:
        - List of next available address block's addresses.
    type: list
    elements: str
    returned: Always
"""

from ansible_collections.infoblox.universal_ddi.plugins.module_utils.modules import UniversalDDIAnsibleModule

try:
    from ipam import AddressBlockApi
    from universal_ddi_client import ApiException
except ImportError:
    pass  # Handled by UniversalDDIAnsibleModule


class NextAvailableAddressBlockInfoModule(UniversalDDIAnsibleModule):
    def __init__(self, *args, **kwargs):
        super(NextAvailableAddressBlockInfoModule, self).__init__(*args, **kwargs)
        self._existing = None
        self._limit = 1000

    def find(self):
        all_results = []
        offset = 0
        while True:
            try:
                resp = AddressBlockApi(self.client).list_next_available_ab(
                    id=self.params["id"], cidr=self.params["cidr"], count=self.params["count"]
                )
                all_results.extend(resp.results)

                if len(resp.results) < self._limit:
                    break
                offset += self._limit

            except ApiException as e:
                self.fail_json(msg=f"Failed to execute command: {e.status} {e.reason} {e.body}")

        return all_results

    def run_command(self):
        result = dict(objects=[])

        if self.check_mode:
            self.exit_json(**result)

        find_results = self.find()

        all_results = []
        for r in find_results:
            # The expected output is a list of addresses as strings.
            # Therefore, we extract only the 'address' field from each object in the results.
            all_results.append(r.address)

        result["objects"] = all_results
        self.exit_json(**result)


def main():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        id=dict(type="str", required=True),
        cidr=dict(type="int", required=True),
        count=dict(type="int", required=False),
    )

    module = NextAvailableAddressBlockInfoModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )
    module.run_command()


if __name__ == "__main__":
    main()
