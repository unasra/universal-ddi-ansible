#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Infoblox Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dhcp_ha_group_info
short_description: Retrieves HA Groups.
description:
    - Retrieves information about existing HA Groups.
    - The HA Group object represents on-prem hosts that can serve the same leases for HA.
version_added: 1.1.0
author: Infoblox Inc. (@infobloxopen)
options:
    id:
        description:
            - ID of the object
        type: str
        required: false
    filters:
        description:
            - Filter dict to filter objects
        type: dict
        required: false
    filter_query:
        description:
            - Filter query to filter objects
        type: str
        required: false
    tag_filters:
        description:
            - Filter dict to filter objects by tags
        type: dict
        required: false
    tag_filter_query:
        description:
            - Filter query to filter objects by tags
        type: str
        required: false

extends_documentation_fragment:
    - infoblox.universal_ddi.common
"""  # noqa: E501

EXAMPLES = r"""
    - name: Get DHCP HA Group Information by filters
      infoblox.universal_ddi.dhcp_ha_group_info:
        filters:
          name: "example_ha_group"
          
    - name: Get DHCP HA Group Information by filter query
      infoblox.universal_ddi.dhcp_ha_group_info:
        filter_query: "name=='example_ha_group'"
        
    - name: Get DHCP HA Group Information by tag filters
      infoblox.universal_ddi.dhcp_ha_group_info:
        tag_filters:
          location: "Site-1"
"""  # noqa: E501

RETURN = r"""
id:
    description:
        - ID of the HA Group object
    type: str
    returned: Always
objects:
    description:
        - HA Group object
    type: list
    elements: dict
    returned: Always
    contains:
        anycast_config_id:
            description:
                - "The resource identifier."
            type: str
            returned: Always
        comment:
            description:
                - "The description for the HA group. May contain 0 to 1024 characters. Can include UTF-8."
            type: str
            returned: Always
        created_at:
            description:
                - "Time when the object has been created."
            type: str
            returned: Always
        hosts:
            description:
                - "The list of hosts."
            type: list
            returned: Always
            elements: dict
            contains:
                address:
                    description:
                        - "The address on which this host listens."
                    type: str
                    returned: Always
                heartbeats:
                    description:
                        - "Last successful heartbeat received from its peer/s. This field is set when the I(collect_stats) is set to I(true) in the I(GET) I(/dhcp/ha_group) request."
                    type: list
                    returned: Always
                    elements: dict
                    contains:
                        peer:
                            description:
                                - "The name of the peer."
                            type: str
                            returned: Always
                        successful_heartbeat:
                            description:
                                - "The timestamp as a string of the last successful heartbeat received from the peer above."
                            type: str
                            returned: Always
                        successful_heartbeat_v6:
                            description:
                                - "The timestamp as a string of the last successful DHCPv6 heartbeat received from the peer above."
                            type: str
                            returned: Always
                host:
                    description:
                        - "The resource identifier."
                    type: str
                    returned: Always
                port:
                    description:
                        - "The HA port."
                    type: int
                    returned: Always
                port_v6:
                    description:
                        - "The HA port used for IPv6 communication."
                    type: int
                    returned: Always
                role:
                    description:
                        - "The role of this host in the HA relationship: I(active) or I(passive)."
                    type: str
                    returned: Always
                state:
                    description:
                        - "The state of DHCP on the host. This field is set when the I(collect_stats) is set to I(true) in the I(GET) I(/dhcp/ha_group) request."
                    type: str
                    returned: Always
                state_v6:
                    description:
                        - "The state of DHCPv6 on the host. This field is set when the I(collect_stats) is set to I(true) in the I(GET) I(/dhcp/ha_group) request."
                    type: str
                    returned: Always
        id:
            description:
                - "The resource identifier."
            type: str
            returned: Always
        ip_space:
            description:
                - "The resource identifier."
            type: str
            returned: Always
        mode:
            description:
                - "The mode of the HA group."
                - "Valid values are:"
                - "* I(active-active): Both on-prem hosts remain active."
                - "* I(active-passive): One on-prem host remains active and one remains passive. When the active on-prem host is down, the passive on-prem host takes over."
                - "* I(advanced-active-passive): One on-prem host may be part of multiple HA groups. When the active on-prem host is down, the passive on-prem host takes over."
            type: str
            returned: Always
        name:
            description:
                - "The name of the HA group. Must contain 1 to 256 characters. Can include UTF-8."
            type: str
            returned: Always
        status:
            description:
                - "Status of the HA group. This field is set when the I(collect_stats) is set to I(true) in the I(GET) I(/dhcp/ha_group) request."
            type: str
            returned: Always
        status_v6:
            description:
                - "Status of the DHCPv6 HA group. This field is set when the I(collect_stats) is set to I(true) in the I(GET) I(/dhcp/ha_group) request."
            type: str
            returned: Always
        tags:
            description:
                - "The tags for the HA group."
            type: dict
            returned: Always
        updated_at:
            description:
                - "Time when the object has been updated. Equals to I(created_at) if not updated after creation."
            type: str
            returned: Always
"""  # noqa: E501

from ansible_collections.infoblox.universal_ddi.plugins.module_utils.modules import UniversalDDIAnsibleModule

try:
    from ipam import HaGroupApi
    from universal_ddi_client import ApiException, NotFoundException
except ImportError:
    pass  # Handled by UniversalDDIAnsibleModule


class HaGroupInfoModule(UniversalDDIAnsibleModule):
    def __init__(self, *args, **kwargs):
        super(HaGroupInfoModule, self).__init__(*args, **kwargs)
        self._existing = None
        self._limit = 1000

    def find_by_id(self):
        try:
            resp = HaGroupApi(self.client).read(self.params["id"])
            return [resp.result]
        except NotFoundException as e:
            return None

    def find(self):
        if self.params["id"] is not None:
            return self.find_by_id()

        filter_str = None
        if self.params["filters"] is not None:
            filter_str = " and ".join([f"{k}=='{v}'" for k, v in self.params["filters"].items()])
        elif self.params["filter_query"] is not None:
            filter_str = self.params["filter_query"]

        tag_filter_str = None
        if self.params["tag_filters"] is not None:
            tag_filter_str = " and ".join([f"{k}=='{v}'" for k, v in self.params["tag_filters"].items()])
        elif self.params["tag_filter_query"] is not None:
            tag_filter_str = self.params["tag_filter_query"]

        all_results = []
        offset = 0

        while True:
            try:
                resp = HaGroupApi(self.client).list(
                    offset=offset, limit=self._limit, filter=filter_str, tfilter=tag_filter_str
                )

                # If no results, set results to empty list
                if not resp.results:
                    resp.results = []

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
            all_results.append(r.model_dump(by_alias=True, exclude_none=True))

        result["objects"] = all_results
        self.exit_json(**result)


def main():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        id=dict(type="str", required=False),
        filters=dict(type="dict", required=False),
        filter_query=dict(type="str", required=False),
        tag_filters=dict(type="dict", required=False),
        tag_filter_query=dict(type="str", required=False),
    )

    module = HaGroupInfoModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[
            ["id", "filters", "filter_query"],
            ["id", "tag_filters", "tag_filter_query"],
        ],
    )
    module.run_command()


if __name__ == "__main__":
    main()
