// Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <string.h>
#include <sys/time.h>

#include <algorithm>
#include <set>

#include "common/danger.h"
#include "posix_translation/epoll_stream.h"
#include "posix_translation/time_util.h"
#include "posix_translation/virtual_file_system.h"

namespace posix_translation {

EPollStream::EPollStream(int fd, int oflag)
    : FileStream(oflag, ""), fd_(fd),
      cond_(&VirtualFileSystem::GetVirtualFileSystem()->mutex()) {
}

EPollStream::~EPollStream() {
}

void EPollStream::OnLastFileRef() {
  // We cannot do this in the destructor because we have cyclic reference
  // (epoll_map_ and listeners_) so ~EPollStream will not be called unless
  // we call StopListeningTo for epoll_map_.
  for (EPollMap::iterator it = epoll_map_.begin(); it != epoll_map_.end();
       ++it) {
    StopListeningTo(it->second.stream_);
  }
  epoll_map_.clear();
}

void EPollStream::HandleNotificationFrom(
    scoped_refptr<FileStream> file, bool is_closing) {
  ALOG_ASSERT(epoll_map_.count(file) != 0,
              "Epoll listener notification from unregistered file");
  if (is_closing) {
    epoll_map_.erase(file);
  }
  // Multiple threads could wait on a level-triggered epoll. We could only
  // use Signal() if all registrations were edge-triggered or one-shot.
  VirtualFileSystem* sys = VirtualFileSystem::GetVirtualFileSystem();
  sys->mutex().AssertAcquired();
  cond_.Broadcast();
}

int EPollStream::epoll_ctl(
    int op, scoped_refptr<FileStream> file, struct epoll_event* event) {
  VirtualFileSystem* sys = VirtualFileSystem::GetVirtualFileSystem();
  EPollMap::iterator it;
  switch (op) {
    case EPOLL_CTL_ADD:
      // TODO(crbug.com/238302): Support edge-based triggering. Without such
      // support the application may be waking up in a busy loop.
      if (event->events & (EPOLLPRI | EPOLLET | EPOLLONESHOT)) {
        ALOGE("Unsupported epoll events: %s",
              arc::GetEpollEventStr(event->events).c_str());
      }
      if (!epoll_map_.insert(std::make_pair(
              file.get(), EPollEntry(file, *event))).second) {
        errno = EEXIST;
        return -1;
      }
      if (!StartListeningTo(file)) {
        errno = EPERM;
        return -1;
      }
      // The spec requires that a blocked epoll_wait() checks for new files.
      sys->mutex().AssertAcquired();
      cond_.Broadcast();
      break;
    case EPOLL_CTL_MOD:
      if (event->events & (EPOLLPRI | EPOLLET | EPOLLONESHOT)) {
        ALOGE("Unsupported epoll events: %s",
              arc::GetEpollEventStr(event->events).c_str());
      }
      it = epoll_map_.find(file);
      if (it == epoll_map_.end()) {
        errno = ENOENT;
        return -1;
      }
      it->second.event_ = *event;
      sys->mutex().AssertAcquired();
      cond_.Broadcast();  // New events may have to unblock epoll_wait().
      break;
    case EPOLL_CTL_DEL:
      if (!epoll_map_.erase(file)) {
        errno = ENOENT;
        return -1;
      }
      StopListeningTo(file);
      break;
    default:
      errno = EINVAL;
      return -1;
  }

  return 0;
}

int EPollStream::epoll_wait(struct epoll_event* events, int maxevents,
                            int timeout) {
  if (!events) {
    errno = EFAULT;
    return -1;
  }
  if (maxevents <= 0) {
    errno = EINVAL;
    return -1;
  }

  const base::TimeTicks time_limit = timeout <= 0 ?
      base::TimeTicks() :  // No timeout.
      base::TimeTicks::Now() + base::TimeDelta::FromMilliseconds(timeout);

  // If timeout is 0, it is just polling. Then, set this flag, so that result
  // will be returned properly.
  bool is_timedout = (timeout == 0);
  while (true) {
    // check all fds in epoll_map_ for relevant events
    // TODO(crbug.com/242633): Enqueue notifications from files and avoid O(N)
    // search.
    int count = 0;
    for (EPollMap::iterator it = epoll_map_.begin(); it != epoll_map_.end();
         ++it) {
      scoped_refptr<FileStream> stream = it->second.stream_;
      const uint32_t event_mask =
          it->second.event_.events | POLLERR | POLLHUP | POLLNVAL;
      uint32_t found_events = stream->GetPollEvents() & event_mask;
      if (found_events) {
        events[count].events = found_events;
        events[count].data = it->second.event_.data;
        count++;
        if (count == maxevents)
          break;
      }
    }

    if (is_timedout || count > 0)
      return count;

    // 'timedout == true' only means that |timeout_rem| has expired. |cond|
    // might or might not have been signaled. To update |count|, we need to
    // run the for-loop above once more.
    is_timedout = internal::WaitUntil(&cond_, time_limit);
  }

  // Should not reach here.
  ALOG_ASSERT(false);
}

ssize_t EPollStream::read(void* buf, size_t count) {
  errno = EINVAL;
  return -1;
}

ssize_t EPollStream::write(const void* buf, size_t count) {
  errno = EINVAL;
  return -1;
}

const char* EPollStream::GetStreamType() const {
  return "epoll";
}

EPollStream::EPollEntry::EPollEntry()
    : stream_(NULL) {
  memset(&event_, 0, sizeof(event_));
}

EPollStream::EPollEntry::EPollEntry(scoped_refptr<FileStream> stream,
                                    struct epoll_event event)
    : stream_(stream), event_(event) {
}

EPollStream::EPollEntry::~EPollEntry() {
}

}  // namespace posix_translation
