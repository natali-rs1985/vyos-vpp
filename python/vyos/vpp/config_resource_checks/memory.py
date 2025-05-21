# Used for memory consumption calculations
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

import psutil

from vyos.utils.cpu import get_core_count
from vyos.vpp.utils import (
    human_memory_to_bytes,
    human_page_memory_to_bytes,
)


def available_memory(config: dict, defaults: dict, skip_cores: int) -> int:
    # We need to use a custom calculation of available memory
    # To reserve 4 GB for system and other (non-VPP) services
    mem_info = psutil.virtual_memory()
    mem_total = mem_info.total
    mem_used = mem_info.used

    if config.get('effective'):
        # Check if there is a config currently active
        # If yes, calculate how much memory it consumes and exclude it
        mem_effective = total_memory_required(
            settings=config['effective'], defaults=defaults
        )
        mem_used = mem_used - mem_effective

    return mem_total - mem_used


def buffer_size(settings: dict, defaults: dict, **kwargs) -> int:
    cpus_count = kwargs.get('cpus_count', get_core_count())
    buffers_per_numa = int(
        settings.get('buffers', {}).get(
            'buffers_per_numa', defaults.get('buffers_per_numa')
        )
    )
    data_size = int(
        settings.get('buffers', {}).get('data_size', defaults.get('data_size'))
    )
    buffers_memory = buffers_per_numa * data_size * cpus_count
    return buffers_memory


def hugepage_size(settings: dict, default_hugepage: str) -> int:
    nr_hugepages = settings.get('host_resources', {}).get('nr_hugepages')
    if nr_hugepages:
        return int(nr_hugepages) * 2 * 1024**2
    else:
        return human_page_memory_to_bytes(default_hugepage)


def netlink_buffer_size(settings: dict, default_buffer: int) -> int:
    return int(settings.get('lcp', {}).get('rx_buffer_size', default_buffer))


def main_heap_page_size(settings: dict, default_main_page: str) -> int:
    heap_page_size = settings.get('memory', {}).get(
        'main_heap_page_size', default_main_page
    )
    return human_page_memory_to_bytes(heap_page_size)


def memory_main_heap(settings: dict, default_heap_size: str) -> int:
    heap_size = settings.get('memory', {}).get('main_heap_size')
    if not heap_size:
        heap_size = default_heap_size
    return human_memory_to_bytes(heap_size)


def ipv6_heap_size(settings: dict, default_ipv6_heap: str) -> int:
    heap_size = settings.get('ipv6', {}).get('heap_size')
    if not heap_size:
        heap_size = default_ipv6_heap
    return human_memory_to_bytes(heap_size)


def total_heap_size(heap_size: int, heap_page_size: int) -> int:
    return (heap_size + heap_page_size - 1) & ~(heap_page_size - 1)


def statseg_size(settings: dict, default_statseg_heap: str) -> int:
    statseg_memory = settings.get('statseg', {}).get('size', default_statseg_heap)
    return human_memory_to_bytes(statseg_memory)


def statseg_page_size(settings: dict) -> int:
    page_size = settings.get('statseg', {}).get('page_size', 'default')
    return human_page_memory_to_bytes(page_size)


def total_statseg_size(_statseg_size: int, _statseg_page: int) -> int:
    return (_statseg_size + _statseg_page - 1) & ~(_statseg_page - 1)


def total_memory_required(settings: dict, defaults: dict) -> int:
    mem_required = hugepage_size(settings, defaults.get('hugepage_size'))
    mem_stats = {
        'memory_buffers': buffer_size(settings, defaults),
        'netlink_buffer_size': netlink_buffer_size(
            settings=settings, default_buffer=defaults.get('netlink_rx_buffer_size')
        ),
        'heap_size': total_heap_size(
            heap_size=memory_main_heap(settings, defaults.get('main_heap_size')),
            heap_page_size=main_heap_page_size(
                settings=settings, default_main_page=defaults.get('main_heap_page_size')
            ),
        ),
        'statseg_size': total_statseg_size(
            _statseg_size=statseg_size(settings, defaults.get('statseg_heap_size')),
            _statseg_page=statseg_page_size(settings),
        ),
        'ipv6_heap_size': ipv6_heap_size(settings, defaults.get('ipv6_heap_size')),
    }

    for stat in mem_stats:
        mem_required += mem_stats[stat]
    return human_memory_to_bytes(mem_required)
