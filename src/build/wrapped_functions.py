# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Define the list of wrapped functions for ARC."""


def get_wrapped_functions():
  wrapped_functions = ['__read_chk',
                       '__recvfrom_chk',
                       '__umask_chk',
                       'abort',
                       'accept',
                       'access',
                       'bind',
                       'chdir',
                       'chmod',
                       'chown',
                       'closedir',
                       'connect',
                       'creat',
                       'dirfd',
                       'dladdr',
                       'dlclose',
                       'dlopen',
                       'dlsym',
                       'epoll_create',
                       'epoll_ctl',
                       'epoll_wait',
                       'eventfd',
                       'exit',
                       'fchdir',
                       'fchmod',
                       'fchown',
                       'fcntl',
                       'fdatasync',
                       'fdopendir',
                       'flock',
                       'fork',
                       'fpathconf',
                       'freeaddrinfo',
                       'fstatfs',
                       'fsync',
                       'ftruncate',
                       'ftruncate64',
                       'futimens',
                       'gai_strerror',
                       'getaddrinfo',
                       'getegid',
                       'geteuid',
                       'getgid',
                       'gethostbyaddr',
                       'gethostbyname',
                       'gethostbyname2',  # bionic doesn't have gethostbyname2_r
                       'gethostbyname_r',
                       'getnameinfo',
                       'getpeername',
                       'getpid',
                       'getpriority',
                       'getresgid',
                       'getresuid',
                       'getrlimit',
                       'getsockname',
                       'getsockopt',
                       'getuid',
                       'inotify_add_watch',
                       'inotify_init',
                       'inotify_rm_watch',
                       'ioctl',
                       'kill',
                       'lchown',
                       'listen',
                       'madvise',
                       'mlock',
                       'mlockall',
                       'mmap',
                       'mount',
                       'mprotect',
                       'mremap',
                       'msync',
                       'munlock',
                       'munlockall',
                       'munmap',
                       'open',
                       'opendir',
                       'pathconf',
                       'pipe',
                       'pipe2',
                       'poll',
                       'pread',
                       'pread64',
                       'pselect',
                       'pthread_create',
                       'pthread_kill',
                       'pthread_setschedparam',
                       'pwrite',
                       'pwrite64',
                       'readdir',
                       'readdir_r',
                       'readlink',
                       'readv',
                       'realpath',
                       'recv',
                       'recvfrom',
                       'recvmsg',
                       'remove',
                       'rename',
                       'rewinddir',
                       'rmdir',
                       'scandir',
                       'sched_setscheduler',
                       'select',
                       'send',
                       'sendmsg',
                       'sendto',
                       'setegid',
                       'seteuid',
                       'setgid',
                       'setpriority',
                       'setregid',
                       'setresgid',
                       'setresuid',
                       'setreuid',
                       'setrlimit',
                       'setsockopt',
                       'setuid',
                       'shutdown',
                       'sigaction',
                       'sigsuspend',
                       'socket',
                       'socketpair',
                       'statfs',
                       'statvfs',
                       'symlink',
                       'syscall',
                       'tgkill',
                       'tkill',
                       'truncate',
                       'truncate64',
                       'umask',
                       'umount',
                       'umount2',
                       'uname',
                       'utime',
                       'utimes',
                       'vfork',
                       'wait',
                       'wait3',
                       'wait4',
                       'waitid',
                       'waitpid',
                       'writev']
  return sorted(wrapped_functions)
