# Default amount of buffers per NUMA (populated CPU socket)
BUFFERS_PER_NUMA = 16384
# Default size of buffer (in bytes)
DATA_SIZE = 2048
# Default hugepage size for VPP
HUGEPAGE_SIZE = '2M'
# Default amount of memory allocated for VPP exclusive usage
MAIN_HEAP_SIZE = '2G'
# Default main heap page size
MAIN_HEAP_PAGE_SIZE = '2M'
# Default size of buffers transferred via netlink
NETLINK_RX_BUFFER_SIZE = 212992
# Default amount of memory allocated for VPP stats segment usage
STATSEG_HEAP_SIZE = '96M'
# Minimal amount of memory required to start VPP
MIN_MEMORY = 8 * 1024**3
# Minimal number of physical CPU cores required to start VPP
MIN_CPUS = 4
# Reserve at least 4 gigabytes of memory
RESERVED_MEM = 4 * 1024**3
# Reserve at least 2 physical cores
RESERVED_CPU_CORES = 2
# Default heap size for IPv6 routes
IPV6_HEAP_SIZE = '32M'
