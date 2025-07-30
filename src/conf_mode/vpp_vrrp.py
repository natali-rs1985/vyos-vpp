#!/usr/bin/env python3
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

import netifaces

from ipaddress import ip_interface
from ipaddress import IPv4Interface
from ipaddress import IPv6Interface

from vyos import ConfigError

from vyos.config import Config
from vyos.configdict import node_changed
from vyos.configdiff import Diff
from vyos.template import is_ipv4
from vyos.template import is_ipv6

from vyos.vpp.utils import cli_ethernet_with_vifs_ifaces
from vyos.vpp.vrrp import Vrrp


vrrp_vr_flags = {
    'PREEMPT': 0x1,
    'ACCEPT': 0x2,
    'UNICAST': 0x4,
    'IPV6': 0x8,
}


def _set_vrrp_flags(config: dict) -> int:
    flags = 0

    if 'no_preempt' not in config:
        flags |= vrrp_vr_flags.get('PREEMPT')
    if 'accept_mode' in config:
        flags |= vrrp_vr_flags.get('ACCEPT')
    if 'peer_address' in config:
        flags |= vrrp_vr_flags.get('UNICAST')
    if is_ipv6(config['address'][0]):
        flags |= vrrp_vr_flags.get('IPV6')

    return flags


def get_config(config=None) -> dict:
    if config:
        conf = config
    else:
        conf = Config()

    base = ['vpp', 'vrrp']

    # Get config_dict with default values
    config = conf.get_config_dict(
        base,
        key_mangling=('-', '_'),
        get_first_key=True,
        no_tag_node_value_mangle=True,
        with_defaults=True,
        with_recursive_defaults=True,
    )

    if not conf.exists(['vpp']):
        config['remove_vpp'] = True
        return config

    # Get effective config as we need full dictionary for deletion
    effective_config = conf.get_config_dict(
        base,
        key_mangling=('-', '_'),
        effective=True,
        get_first_key=True,
        no_tag_node_value_mangle=True,
    )

    if not config:
        config['remove'] = True

    changed_groups = node_changed(
        conf,
        base + ['group'],
        key_mangling=('-', '_'),
        recursive=True,
        expand_nodes=Diff.DELETE | Diff.ADD,
    )

    config.update(
        {
            'changed_groups': changed_groups,
            'vpp_ifaces': cli_ethernet_with_vifs_ifaces(conf),
        }
    )

    if effective_config:
        config.update({'effective': effective_config})

    return config


def verify(config):
    if 'remove' in config or 'remove_vpp' in config:
        return None

    if 'group' not in config:
        raise ConfigError('Group is required but not set in VRRP')

    used_vrid_if = []
    used_addresses = []
    for group, group_config in config['group'].items():
        # Check required fields
        if 'vrid' not in group_config:
            raise ConfigError(f'VRID is required but not set in VRRP group "{group}"')

        if 'interface' not in group_config:
            raise ConfigError(
                f'Interface is required but not set in VRRP group "{group}"'
            )

        if 'address' not in group_config:
            raise ConfigError(
                f'Virtual IP address is required but not set in VRRP group "{group}"'
            )

        interface = group_config['interface']
        vrid = group_config['vrid']

        if interface not in config.get('vpp_ifaces'):
            raise ConfigError(f'Interface {interface} must be a VPP interface for VRRP')
        # Verify interface has address assigned
        if netifaces.AF_INET not in netifaces.ifaddresses(interface):
            raise ConfigError(f'Interface {interface} has no IP address assigned')

        # Cannot use the same virtual address for several VRRP VRs
        for address in group_config['address']:
            if address in used_addresses:
                raise ConfigError(
                    f'Virtual address "{address}" is already in use in another group!'
                )
            used_addresses.append(address)

        vaddrs = list(map(lambda i: ip_interface(i), group_config['address']))
        vaddrs4 = list(filter(lambda x: isinstance(x, IPv4Interface), vaddrs))
        vaddrs6 = list(filter(lambda x: isinstance(x, IPv6Interface), vaddrs))

        # VPP VRRP doesn't allow mixing IPv4 and IPv6 in one group.
        if vaddrs4 and vaddrs6:
            raise ConfigError(
                f'VRRP group "{group}" mixes IPv4 and IPv6 virtual addresses, this is not allowed.\n'
                'Create individual groups for IPv4 and IPv6!'
            )

        if vaddrs4:
            tmp = {'interface': interface, 'vrid': vrid, 'ipver': 'IPv4'}
            if tmp in used_vrid_if:
                raise ConfigError(
                    f'VRID "{vrid}" can only be used once on interface {interface}" with address family IPv4!'
                )
            used_vrid_if.append(tmp)

            if 'peer_address' in group_config:
                for peer_address in group_config['peer_address']:
                    if is_ipv6(peer_address):
                        raise ConfigError(
                            f'VRRP group "{group}" uses IPv4 but peer-address {peer_address} is IPv6!'
                        )

        if vaddrs6:
            tmp = {'interface': interface, 'vrid': vrid, 'ipver': 'IPv6'}
            if tmp in used_vrid_if:
                raise ConfigError(
                    f'VRID "{vrid}" can only be used once on interface "{interface}" with address family IPv6!'
                )
            used_vrid_if.append(tmp)

            if 'peer_address' in group_config:
                for peer_address in group_config['peer_address']:
                    if is_ipv4(peer_address):
                        raise ConfigError(
                            f'VRRP group "{group}" uses IPv6 but peer-address {peer_address} is IPv4!'
                        )


def generate(config):
    pass


def apply(config):
    if 'remove_vpp' in config:
        return None

    vrrp = Vrrp()

    for group, vrrp_config in config.get('effective', {}).get('group', {}).items():
        if group in config.get('changed_groups'):
            vrrp.delete_vrrp_vr(
                interface=vrrp_config['interface'],
                vrid=int(vrrp_config['vrid']),
                priority=int(vrrp_config.get('priority', 100)),
                interval=int(vrrp_config.get('advertise_interval', 1)),
                flags=_set_vrrp_flags(vrrp_config),
                addrs=vrrp_config['address'],
            )

    if 'remove' in config:
        return None

    # Add VRRP or change VR
    for group, vrrp_config in config.get('group', {}).items():
        vrrp.add_vrrp_vr(
            interface=vrrp_config['interface'],
            vrid=int(vrrp_config['vrid']),
            priority=int(vrrp_config['priority']),
            interval=int(vrrp_config['advertise_interval']),
            flags=_set_vrrp_flags(vrrp_config),
            addrs=vrrp_config['address'],
        )

        if 'peer_address' in vrrp_config:
            vrrp.set_vrrp_peers(
                interface=vrrp_config['interface'],
                vrid=int(vrrp_config['vrid']),
                is_ipv6=is_ipv6(vrrp_config.get('peer_address', [])[0]),
                addrs=vrrp_config.get('peer_address', []),
            )

        # start or shutdown protocol for VRRP VR
        vrrp.start_stop_proto_vrrp_vr(
            vrid=int(vrrp_config['vrid']),
            interface=vrrp_config['interface'],
            is_ipv6=is_ipv6(vrrp_config['address'][0]),
            is_start=False if 'disable' in vrrp_config else True,
        )


if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
