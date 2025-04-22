# Used for verifying configuration vpp interfaces
#
# Copyright (C) 2023 VyOS Inc.
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

import psutil

from vyos import ConfigError
from vyos.utils.cpu import get_core_count as total_core_count

from vyos.vpp.control_host import get_eth_driver
from vyos.vpp.config_resource_checks import constants
from vyos.vpp.config_resource_checks import cpu as cpu_checks, memory as memory_checks
from vyos.vpp.utils import bytes_to_human_memory


def verify_vpp_remove_kernel_interface(config: dict):
    """Common verify for removed kernel-interfaces.
    Verify that removed kernel interface are not used in 'vpp kernel-interfaces'.

    Example:
      delete vpp interfaces gre|vxlan <tag>X kernel-interface vpp-tunX
      set vpp kernel-interface vpp-tunX
    """
    if (
        'remove' in config
        and 'kernel_interface_removed' in config
        and 'vpp_kernel_interfaces' in config
    ):
        removed_interfaces = config['kernel_interface_removed']
        used_interfaces = config['vpp_kernel_interfaces']

        for interface in removed_interfaces:
            if interface in used_interfaces:
                raise ConfigError(
                    f'"{interface}" is still in use within "vpp kernel-interfaces". '
                    'Please remove it before proceeding.'
                )


def verify_vpp_change_kernel_interface(config: dict):
    """Common verify for changed kernel-interface

    Example:
      set vpp interfaces gre|vxlan <tag> kernel-interface vpp-tunX'
      commit
      set vpp interfaces gre|vxlan <tag> kernel-interface vpp-tunY'
      commit

    check if we have kernel interface config 'vpp kernel-interface vpp-tunX'
    """
    kernel_interface_removed = config.get('kernel_interface_removed', [])
    vpp_kernel_interfaces = config.get('vpp_kernel_interfaces', {})

    for interface in kernel_interface_removed:
        if interface in vpp_kernel_interfaces:
            raise ConfigError(
                f'interface "{interface}" is still in use within "vpp kernel-interfaces". '
                f'Please remove it "vpp kernel-interface {interface}" before proceeding.'
            )


def verify_vpp_exists_kernel_interface(config: dict):
    """Verify is a kernel-interface already created by another VPP LCP pair

    Example:
      set vpp interfaces vxlan vxlan10 kernel-interface vpp-tun10'
      commit
      set vpp interfaces vxlan vxlan20 kernel-interface vpp-tun10'
      commit
    """
    kernel_interface = config.get('kernel_interface', '')
    vpp_interface = config.get('ifname', '')
    candidate_kernel_interfaces = config.get('candidate_kernel_interfaces', [])

    for candidate_kernel_iface in candidate_kernel_interfaces:
        if (
            vpp_interface != candidate_kernel_iface[0]
            and kernel_interface == candidate_kernel_iface[1]
        ):
            raise ConfigError(
                f'Kernel interface "{kernel_interface}" is already configured for {candidate_kernel_iface[0]}. '
                'Duplicates are not allowed.'
            )


def verify_vpp_remove_xconnect_interface(config: dict):
    if not config.get('remove'):
        return
    for xconn_member, xconn_iface in config.get('xconn_members').items():
        if xconn_member == config.get('ifname'):
            raise ConfigError(
                f'interface "{xconn_member}" is still in use within "vpp interfaces xconnect". '
                f'Please remove it from "vpp interface xconnect {xconn_iface}" before proceeding.'
            )


def verify_vpp_tunnel_source_address(config: dict):
    from vyos.utils.network import is_intf_addr_assigned

    address = config.get('source_address')
    for iface in config.get('vpp_ether_vif_ifaces', []):
        if is_intf_addr_assigned(iface, address):
            return True

    raise ConfigError(
        f'Source address "{address}" is not assigned on any Ethernet or VIF interface!'
    )


def verify_dev_driver(iface_name: str, driver_type: str) -> bool:
    # Lists of drivers compatible with DPDK and XDP
    drivers_dpdk: list[str] = [
        'atlantic',
        'bnx2x',
        'e1000',
        'ena',
        'gve',
        'hv_netvsc',
        'i40e',
        'ice',
        'igc',
        'ixgbe',
        'liquidio',
        'mlx4_core',
        'mlx5_core',
        'qede',
        'sfc',
        'tap',
        'tun',
        'virtio_net',
        'vmxnet3',
    ]

    drivers_xdp: list[str] = [
        'atlantic',
        'ena',
        'gve',
        'hv_netvsc',
        'i40e',
        'ice',
        'igb',
        'igc',
        'ixgbe',
        'mlx4_core',
        'mlx5_core',
        'qede',
        'sfc',
        'tap',
        'tun',
        'virtio_net',
        'vmxnet3',
    ]

    driver: str = get_eth_driver(iface_name)

    if driver_type == 'dpdk':
        if driver in drivers_dpdk:
            return True
    elif driver_type == 'xdp':
        if driver in drivers_xdp:
            return True
    else:
        raise ConfigError(f'"Driver type {driver_type} is wrong')

    return False


def verify_vpp_minimum_cpus():
    if total_core_count() < constants.MIN_CPUS:
        raise ConfigError(
            'This system does not meet minimal requirements for VPP:\n'
            f'Minimum {constants.MIN_CPUS} CPU cores are required.\n'
        )


def verify_vpp_minimum_memory():
    total_memory = round(psutil.virtual_memory().total / (1024**3))
    min_mem = round(constants.MIN_MEMORY / (1024**3))
    if total_memory < min_mem:
        raise ConfigError(
            'This system does not meet minimal requirements for VPP:\n'
            f'Minimum {min_mem} GB of RAM are required.\n'
        )


def verify_vpp_memory_available(config: dict):
    available_memory = memory_checks.available_memory(config)
    memory_required = memory_checks.total_memory_required(config['settings'])

    if memory_required > available_memory:
        raise ConfigError(
            'Not enough free memory to start VPP:\n'
            f'available: {round(available_memory / 1024 ** 3, 1)}GB\n'
            f'required: {round(memory_required / 1024 ** 3, 1)}GB\n'
        )


def verify_vpp_cpus_available(cpus: int, skipped: int, workers: int):
    available_cores = cpus - 1 - skipped

    if workers > available_cores:
        raise ConfigError(
            f'Not enough free CPU cores for {workers} VPP workers '
            f'(reduce to {available_cores} or less)\n'
        )


def verify_vpp_settings_cpu_skip_cores(skip_cores: int):
    # The number of skipped cores must not be greater than
    #   available CPU cores in the system - 1 for main thread
    cpu_cores = cpu_checks.available_core_count() - 1

    if skip_cores > cpu_cores:
        raise ConfigError(
            f'The system does not have enough available CPUs to skip '
            f'(reduce "cpu skip-cores" to {cpu_cores} or less)'
        )


def verify_vpp_settings_cpu_and_corelist_workers(settings: dict):
    if (
        'corelist_workers' in settings or 'workers' in settings
    ) and 'main_core' not in settings:
        raise ConfigError('"cpu main-core" is required but not set!')

    if 'corelist_workers' in settings and 'workers' in settings:
        raise ConfigError(
            '"cpu corelist-workers" and "cpu workers" cannot be used at the same time!'
        )


def verify_vpp_settings_cpu_workers(skip_cores: int, config: dict) -> int:
    workers = int(config.get('settings', {}).get('cpu', {}).get('workers', 0))
    try:
        # There should be enough CPU cores for the workers specified
        verify_vpp_cpus_available(
            cpus=cpu_checks.available_core_count(),
            skipped=skip_cores,
            workers=workers,
        )
        # Also there must be enough memory for workers' buffer
        verify_vpp_memory_available(config)
    except ConfigError as e:
        raise e

    return workers


def verify_vpp_settings_cpu_corelist_workers(
    cpus: int, main_core: int, workers: str
) -> int:
    try:
        all_core_nums = cpu_checks.worker_core_numbers(
            iface='cpu corelist', worker_ranges=workers
        )
    except ValueError as e:
        raise ConfigError(str(e))
    else:
        if main_core in all_core_nums:
            raise ConfigError(
                f'"cpu main-core {main_core}" must not be included in the corelist-workers!'
            )

        if not all(el in cpus for el in all_core_nums):
            raise ConfigError('"cpu corelist-workers" is not correct')

        return len(all_core_nums)


def verify_vpp_nat44_workers(workers: int, nat44_workers: str):
    try:
        nat_workers = cpu_checks.worker_core_numbers(
            iface='nat44', worker_ranges=nat44_workers
        )
    except ValueError as e:
        raise ConfigError(str(e))
    else:
        if not all(el in list(range(workers)) for el in nat_workers):
            raise ConfigError('"nat44" is not correct')


def verify_vpp_settings_heap_size(settings: dict):
    main_heap_size = memory_checks.memory_main_heap(settings)
    main_heap_page_size = memory_checks.main_heap_page_size(settings)

    if main_heap_size < 51 << 20:
        raise ConfigError(
            f'The main heap size must be greater than or equal to {constants.MAIN_HEAP_SIZE}'
        )

    readable_heap_page = bytes_to_human_memory(main_heap_page_size, 'K')

    if main_heap_page_size > main_heap_size:
        raise ConfigError(
            f'The main heap size must be greater than or equal to page-size({readable_heap_page})'
        )


def verify_vpp_statseg_size(settings: dict):
    statseg_size = memory_checks.statseg_size(settings)

    if 'size' in settings['statseg']:
        if statseg_size < 1 << 20:
            raise ConfigError('The statseg size must be greater than or equal to 1M')

    if 'page_size' in settings['statseg']:
        statseg_page_size = memory_checks.statseg_page_size(settings)
        if statseg_page_size > statseg_size:
            readable_statseg_page = bytes_to_human_memory(statseg_page_size, 'K')
            raise ConfigError(
                f'The statseg size must be greater than or equal to page-size({readable_statseg_page})'
            )


def verify_vpp_interfaces_dpdk_num_queues(qtype: str, num_queues: int):
    available_cpus = cpu_checks.cpu_count()

    if num_queues > available_cpus:
        raise ConfigError(
            f'The number of {qtype} queues cannot be greater than the number of available CPUs:\n'
            f'available: {available_cpus}\n'
            f'requested: {num_queues}'
        )
