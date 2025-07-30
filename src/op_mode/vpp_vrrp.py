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

import json
import sys
import typing
from tabulate import tabulate

import vyos.opmode
from vyos.configquery import ConfigTreeQuery
from vyos.template import is_ipv6

from vyos.vpp import VPPControl


vrrp_flags = {
    'PREEMPT': 0x1,
    'ACCEPT': 0x2,
    'UNICAST': 0x4,
    'IPV6': 0x8,
}

vrrp_state_map = {
    0: 'INIT',
    1: 'BACKUP',
    2: 'MASTER',
    3: 'INTF_DOWN',
}


def _verify(func):
    """Decorator checks if config for VPP NAT44 exists"""
    from functools import wraps

    @wraps(func)
    def _wrapper(*args, **kwargs):
        config = ConfigTreeQuery()
        base = 'vpp vrrp group'
        if not config.exists(base):
            raise vyos.opmode.UnconfiguredSubsystem(f'{base} is not configured')

        return func(*args, **kwargs)

    return _wrapper


def _get_raw_output(data_dump):
    data = json.loads(json.dumps(data_dump._asdict(), default=str))
    return data


def _get_raw_output_vrrps(data_dump):
    out = []
    for data in data_dump:
        out.append(
            {
                'config': _get_raw_output(data.config),
                'runtime': _get_raw_output(data.runtime),
                'addrs': [str(addr) for addr in data.addrs],
            }
        )
    return out


def _get_vrrp_group_from_config(vpp, vrrp):
    config = ConfigTreeQuery()
    vrrp_config = config.get_config_dict(
        ['vpp', 'vrrp', 'group'],
        key_mangling=('-', '_'),
    )
    vr_id = vrrp['config']['vr_id']
    ifname = vpp.get_interface_name(vrrp['config']['sw_if_index'])
    _is_ipv6 = bool(vrrp['config']['flags'] & vrrp_flags.get('IPV6'))
    group = next(
        (
            name
            for name, cfg in vrrp_config['group'].items()
            if int(cfg['vrid']) == vr_id
            and cfg['interface'] == ifname
            and is_ipv6(cfg['address'][0]) == _is_ipv6
        ),
        '',
    )
    return group


def _get_formatted_output_vrrps(vpp, vrrp_list):
    data_entries = []
    for vrrp in vrrp_list:
        vrrp_config = vrrp['config']

        values = [
            vrrp['group'],
            vpp.get_interface_name(vrrp_config['sw_if_index']),
            vrrp_config['vr_id'],
            vrrp_state_map.get(vrrp['runtime']['state'], 'UNKNOWN'),
            vrrp_config['priority'],
            ', '.join(vrrp['addrs']),
        ]
        data_entries.append(values)

    headers = [
        'Name',
        'Interface',
        'VRID',
        'State',
        'Priority',
        'Address',
    ]
    out = sorted(data_entries, key=lambda x: x[2])
    return tabulate(out, headers=headers, tablefmt='simple')


@_verify
def show_vrrp(raw: bool, group: typing.Optional[str]):
    vpp = VPPControl()
    vrrps_dump = vpp.api.vrrp_vr_dump()
    vrrps: list[dict] = _get_raw_output_vrrps(vrrps_dump)

    for vrrp in vrrps:
        vrrp['group'] = _get_vrrp_group_from_config(vpp, vrrp)

    if group:
        vrrps = [vrrp for vrrp in vrrps if vrrp['group'] == group]

    if raw:
        return vrrps

    else:
        return _get_formatted_output_vrrps(vpp, vrrps)


if __name__ == '__main__':
    try:
        res = vyos.opmode.run(sys.modules[__name__])
        if res:
            print(res)
    except (ValueError, vyos.opmode.Error) as e:
        print(e)
        sys.exit(1)
