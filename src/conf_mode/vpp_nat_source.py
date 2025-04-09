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

from vyos.config import Config, config_dict_merge
from vyos import ConfigError
from vyos.vpp.nat.nat44 import Nat44


def get_config(config=None) -> dict:
    if config:
        conf = config
    else:
        conf = Config()

    base = ['vpp', 'nat44', 'source']

    # Get config_dict without default values
    config = conf.get_config_dict(
        base,
        key_mangling=('-', '_'),
        get_first_key=True,
        no_tag_node_value_mangle=True,
    )

    # Get effective config as we need full dictionary per interface delete
    effective_config = conf.get_config_dict(
        base,
        key_mangling=('-', '_'),
        effective=True,
        get_first_key=True,
        no_tag_node_value_mangle=True,
    )

    if not config:
        config['remove'] = True

    # Get default values and merge
    default_values = conf.get_config_defaults(**config.kwargs, recursive=True)
    config = config_dict_merge(default_values, config)

    if effective_config:
        config.update({'effective': effective_config})

    return config


def verify(config):
    if 'remove' in config:
        return None

    required_keys = {'inside_interface', 'outside_interface'}
    missing_keys = required_keys - set(config.keys())
    if missing_keys:
        raise ConfigError(
            f"Required options are missing: {', '.join(missing_keys).replace('_', '-')}"
        )

    pools = config.get('translation', {}).get('pool')
    if not pools:
        raise ConfigError('Translation pool is required')

    for num, pool in pools.items():
        if 'address' not in pool:
            raise ConfigError(f'Source NAT translation pool {num} missing address')


def generate(config):
    pass


def apply(config):
    # Delete NAT source
    if 'effective' in config:
        remove_config = config.get('effective')
        interfaces_in = remove_config.get('inside_interface')
        interface_out = remove_config.get('outside_interface')
        pools = remove_config.get('translation', {}).get('pool')

        n = Nat44(interface_out)
        n.delete_nat44_interface_outside()
        for interface in interfaces_in:
            n.delete_nat44_interface_inside(interface)
        for pool in pools.values():
            n.delete_nat44_address_range(pool['address'])

    if 'remove' in config:
        return None

    # Add NAT44
    interfaces_in = config.get('inside_interface')
    interface_out = config.get('outside_interface')
    sessions = int(config.get('limits').get('per_thread_sessions'))
    pools = config.get('translation', {}).get('pool')

    n = Nat44(interface_out)
    n.enable_nat44_ed()
    n.set_nat44_session_limit(sessions)
    n.add_nat44_interface_outside()
    for interface in interfaces_in:
        n.add_nat44_interface_inside(interface)
    for pool in pools.values():
        n.add_nat44_address_range(pool['address'])


if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
