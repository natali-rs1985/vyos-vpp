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


class Vrrp:
    def __init__(self):
        self.vpp = VPPControl()

    def add_vrrp_vr(self, interface, vrid, priority, interval, flags, addrs):
        """Add new VRRP VR"""
        self.vpp.api.vrrp_vr_add_del(
            vr_id=vrid,
            is_add=True,
            sw_if_index=self.vpp.get_sw_if_index(interface),
            priority=priority,
            interval=interval * 100,
            flags=flags,
            n_addrs=len(addrs),
            addrs=addrs,
        )

    def delete_vrrp_vr(self, interface, vrid, priority, interval, flags, addrs):
        """Delete existing VRRP VR"""
        self.vpp.api.vrrp_vr_add_del(
            vr_id=vrid,
            is_add=False,
            sw_if_index=self.vpp.get_sw_if_index(interface),
            priority=priority,
            interval=interval * 100,
            flags=flags,
            n_addrs=len(addrs),
            addrs=addrs,
        )

    def start_stop_proto_vrrp_vr(self, vrid, interface, is_ipv6, is_start):
        """Start or shutdown the VRRP protocol for a VR"""
        self.vpp.api.vrrp_vr_start_stop(
            vr_id=vrid,
            sw_if_index=self.vpp.get_sw_if_index(interface),
            is_ipv6=is_ipv6,
            is_start=is_start,
        )

    def set_vrrp_peers(self, interface, vrid, is_ipv6, addrs):
        """Set unicast peers for a VR"""
        self.vpp.api.vrrp_vr_set_peers(
            sw_if_index=self.vpp.get_sw_if_index(interface),
            vr_id=vrid,
            is_ipv6=is_ipv6,
            n_addrs=len(addrs),
            addrs=addrs,
        )
