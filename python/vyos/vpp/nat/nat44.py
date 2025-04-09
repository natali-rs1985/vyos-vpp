#
# Copyright (C) 2025 VyOS Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from vyos.vpp import VPPControl


# NAT44 flags
NAT_IS_NONE = 0x00
NAT_IS_ADDR_ONLY = 0x08
NAT_IS_OUTSIDE = 0x10
NAT_IS_INSIDE = 0x20


class Nat44:
    def __init__(
        self,
        interface_out: str,
    ):
        self.interface_out = interface_out
        self.vpp = VPPControl()

    def enable_nat44_ed(self):
        """Enable NAT44 endpoint dependent plugin
        Example:
            from vyos.vpp.nat import Nat44
            nat44 = Nat44()
            nat44.enable_nat44_ed()
        https://github.com/FDio/vpp/blob/stable/2410/src/plugins/nat/nat44-ed/nat44_ed.api
        """
        self.vpp.api.nat44_ed_plugin_enable_disable(enable=True)

    def enable_nat44_ei(self):
        """Enable NAT44 endpoint independent plugin
        Example:
            from vyos.vpp.nat import Nat44
            nat44 = Nat44()
            nat44.enable_nat44_ei()
        """
        self.vpp.api.nat44_ei_plugin_enable_disable(enable=True)

    def enable_nat44_forwarding(self):
        """Enable NAT44 forwarding
        Example:
            from vyos.vpp.nat import Nat44
            nat44 = Nat44()
            nat44.enable_nat44_forwarding()
        """
        self.vpp.api.nat44_forwarding_enable_disable(enable=True)

    def disable_nat44_forwarding(self):
        """Disable NAT44 forwarding
        Example:
            from vyos.vpp.nat import Nat44
            nat44 = Nat44()
            nat44.disable_nat44_forwarding()
        """
        self.vpp.api.nat44_forwarding_enable_disable(enable=False)

    def add_nat44_out_interface(self):
        """Add NAT44 output interface
        Example:
            from vyos.vpp.nat import Nat44
            nat44 = Nat44('eth0')
            nat44.add_nat44_out_interface()
        """
        self.vpp.api.nat44_ed_add_del_output_interface(
            sw_if_index=self.vpp.get_sw_if_index(self.interface_out),
            is_add=True,
        )

    def delete_nat44_out_interface(self):
        """Delete NAT44 output interface"""
        self.vpp.api.nat44_ed_add_del_output_interface(
            sw_if_index=self.vpp.get_sw_if_index(self.interface_out),
            is_add=False,
        )

    def add_nat44_interface_inside(self, interface):
        """Add NAT44 interface"""
        self.vpp.api.nat44_interface_add_del_feature(
            flags=NAT_IS_INSIDE,
            sw_if_index=self.vpp.get_sw_if_index(interface),
            is_add=True,
        )

    def delete_nat44_interface_inside(self, interface):
        """Delete NAT44 interface"""
        self.vpp.api.nat44_interface_add_del_feature(
            flags=NAT_IS_INSIDE,
            sw_if_index=self.vpp.get_sw_if_index(interface),
            is_add=False,
        )

    def add_nat44_interface_outside(self):
        """Add NAT44 interface"""
        self.vpp.api.nat44_interface_add_del_feature(
            flags=NAT_IS_OUTSIDE,
            sw_if_index=self.vpp.get_sw_if_index(self.interface_out),
            is_add=True,
        )

    def delete_nat44_interface_outside(self):
        """Delete NAT44 interface"""
        self.vpp.api.nat44_interface_add_del_feature(
            flags=NAT_IS_OUTSIDE,
            sw_if_index=self.vpp.get_sw_if_index(self.interface_out),
            is_add=False,
        )

    def add_nat44_address_range(self, translation_pool):
        """Add NAT44 address range"""
        if '-' not in translation_pool:
            first_ip_address = last_ip_address = translation_pool
        else:
            first_ip_address, last_ip_address = translation_pool.split('-')
        self.vpp.api.nat44_add_del_address_range(
            first_ip_address=first_ip_address,
            last_ip_address=last_ip_address,
            is_add=True,
        )

    def delete_nat44_address_range(self, translation_pool):
        """Delete NAT44 address range"""
        if '-' not in translation_pool:
            first_ip_address = last_ip_address = translation_pool
        else:
            first_ip_address, last_ip_address = translation_pool.split('-')
        self.vpp.api.nat44_add_del_address_range(
            first_ip_address=first_ip_address,
            last_ip_address=last_ip_address,
            is_add=False,
        )

    def set_nat44_session_limit(self, sessions):
        """Set NAT44 maximum number of sessions per worker thread"""
        self.vpp.api.nat44_set_session_limit(session_limit=sessions)

    def enable_ipfix(self):
        """Enable NAT44 IPFIX logging"""
        self.vpp.api.nat44_ei_ipfix_enable_disable(enable=True)


class Nat44Static(Nat44):
    def __init__(self):
        self.vpp = VPPControl()

    def add_outside_interface(self, interface_out):
        self.interface_out = interface_out
        self.add_nat44_interface_outside()

    def delete_outside_interface(self, interface_out):
        self.interface_out = interface_out
        self.delete_nat44_interface_outside()

    def add_nat44_static_mapping(
        self, local_ip, external_ip, local_port, external_port, protocol
    ):
        """Add NAT44 static mapping"""
        self.vpp.api.nat44_add_del_static_mapping_v2(
            local_ip_address=local_ip,
            external_ip_address=external_ip,
            protocol=protocol,
            local_port=local_port,
            external_port=external_port,
            flags=NAT_IS_ADDR_ONLY if not (protocol or local_port) else NAT_IS_NONE,
            is_add=True,
        )

    def delete_nat44_static_mapping(
        self, local_ip, external_ip, local_port, external_port, protocol
    ):
        """Delete NAT44 static mapping"""
        self.vpp.api.nat44_add_del_static_mapping_v2(
            local_ip_address=local_ip,
            external_ip_address=external_ip,
            protocol=protocol,
            local_port=local_port,
            external_port=external_port,
            flags=NAT_IS_ADDR_ONLY if not (protocol or local_port) else NAT_IS_NONE,
            is_add=False,
        )
