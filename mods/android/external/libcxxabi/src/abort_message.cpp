//===------------------------- abort_message.cpp --------------------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is dual licensed under the MIT and the University of Illinois Open
// Source Licenses. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//

#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include "abort_message.h"

// ARC MOD BEGIN
// ARC does not support <android/set_abort_message.h>
#if defined(__BIONIC__) && !defined(HAVE_ARC)
// ARC MOD END
#include <android/set_abort_message.h>
#include <syslog.h>
#endif

#pragma GCC visibility push(hidden)

#if __APPLE__
#   if defined(__has_include) && __has_include(<CrashReporterClient.h>)
#       define HAVE_CRASHREPORTERCLIENT_H 1
#       include <CrashReporterClient.h>
#   endif
#endif

__attribute__((visibility("hidden"), noreturn))
void abort_message(const char* format, ...)
{
    // write message to stderr
#if __APPLE__
    fprintf(stderr, "libc++abi.dylib: ");
#endif
    va_list list;
    va_start(list, format);
    vfprintf(stderr, format, list);
    va_end(list);
    fprintf(stderr, "\n");

#if __APPLE__ && HAVE_CRASHREPORTERCLIENT_H
    // record message in crash report
    char* buffer;
    va_list list2;
    va_start(list2, format);
    vasprintf(&buffer, format, list2);
    va_end(list2);
    CRSetCrashLogMessage(buffer);
    // ARC MOD BEGIN
#elif defined(__BIONIC__) && !defined(HAVE_ARC)
    // ARC MOD END
    char* buffer;
    va_list list2;
    va_start(list2, format);
    vasprintf(&buffer, format, list2);
    va_end(list2);

    // Show error in tombstone.
    android_set_abort_message(buffer);

    // Show error in logcat.
    openlog("libc++abi", 0, 0);
    syslog(LOG_CRIT, "%s", buffer);
    closelog();
#endif

    abort();
}

#pragma GCC visibility pop
