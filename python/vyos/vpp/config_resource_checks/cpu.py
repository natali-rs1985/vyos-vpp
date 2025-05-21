# Used for validating estimated CPU/physical cores use
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

from vyos.utils.cpu import get_available_cpus


def __available_cpus(reserved_cpus: int, skip_cores: int) -> list[int]:
    # We need to reserve at least 2 cores for services other than VPP if possible
    # Get all available physical cores - use set to filter out unique values
    cpus = set(map(lambda el: el['core'], get_available_cpus()))
    cpus = list(cpus)

    if len(cpus) > reserved_cpus:
        skip_cores += reserved_cpus

    return cpus[skip_cores:]


def available_core_count(reserved_cpus: int, skip_cores: int) -> int:
    return len(__available_cpus(reserved_cpus, skip_cores))


def available_cpus(reserved_cpus: int, skip_cores: int) -> list:
    # Available CPUs are all CPUs without first N skipped cores that will not be used
    return __available_cpus(reserved_cpus, skip_cores)


def worker_core_numbers(iface: str, worker_ranges: list) -> list:
    all_core_numbers = []
    for worker_range in worker_ranges:
        core_numbers = worker_range.split('-')

        if int(core_numbers[0]) > int(core_numbers[-1]):
            raise ValueError(
                f'Range for "{iface} workers {worker_range}" is not correct'
            )

        all_core_numbers.extend(range(int(core_numbers[0]), int(core_numbers[-1]) + 1))

    return all_core_numbers
