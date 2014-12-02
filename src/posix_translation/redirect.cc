// Copyright 2014 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "posix_translation/redirect.h"

#include <dirent.h>
#include <utility>

#include "base/strings/string_util.h"
#include "common/arc_strace.h"
#include "common/file_util.h"
#include "posix_translation/dir.h"
#include "posix_translation/directory_file_stream.h"
#include "posix_translation/path_util.h"

namespace posix_translation {

RedirectHandler::RedirectHandler(
    FileSystemHandler* underlying,
    const std::vector<std::pair<std::string, std::string> >& symlinks)
    : FileSystemHandler("RedirectHandler"),
      is_initialized_(false), underlying_(underlying) {
  ALOG_ASSERT(underlying);
  for (size_t i = 0; i < symlinks.size(); ++i)
    AddSymlink(symlinks[i].first, symlinks[i].second);
}

RedirectHandler::~RedirectHandler() {
}

bool RedirectHandler::IsInitialized() const {
  return underlying_->IsInitialized() && is_initialized_;
}

void RedirectHandler::Initialize() {
  ALOG_ASSERT(!IsInitialized());
  if (!underlying_->IsInitialized())
    underlying_->Initialize();
  if (!is_initialized_) {
    is_initialized_ = true;
    // Note: Once you remove gmock from posix_translation/, you can call
    // this->symlink() here for the paths passed to the constructor. Right
    // now, doing so breaks some unit tests because this->symlink() calls
    // into the |underlying_| handler which may end up calling gmock mocks.
  }
}

void RedirectHandler::OnMounted(const std::string& path) {
  return underlying_->OnMounted(path);
}

void RedirectHandler::OnUnmounted(const std::string& path) {
  return underlying_->OnUnmounted(path);
}

void RedirectHandler::InvalidateCache() {
  return underlying_->InvalidateCache();
}

void RedirectHandler::AddToCache(const std::string& path,
                                 const PP_FileInfo& file_info,
                                 bool exists) {
  return underlying_->AddToCache(path, file_info, exists);
}

bool RedirectHandler::IsWorldWritable(const std::string& pathname) {
  return underlying_->IsWorldWritable(pathname);
}

std::string RedirectHandler::SetPepperFileSystem(
    const pp::FileSystem* pepper_file_system,
    const std::string& mount_source_in_pepper_file_system,
    const std::string& mount_dest_in_vfs) {
  return underlying_->SetPepperFileSystem(
      pepper_file_system,
      mount_source_in_pepper_file_system,
      mount_dest_in_vfs);
}

int RedirectHandler::mkdir(const std::string& pathname, mode_t mode) {
  // Note: |pathname| is already canonicalized in VFS. VFS calls
  // RedirectHandler::readlink() and resolves the symlink before
  // calling into this method. The same is true for other methods too.
  return underlying_->mkdir(pathname, mode);
}

scoped_refptr<FileStream> RedirectHandler::open(
      int fd, const std::string& pathname, int oflag, mode_t cmode) {
  scoped_refptr<FileStream> stream =
      underlying_->open(fd, pathname, oflag, cmode);
  if (stream && (stream->oflag() & O_DIRECTORY)) {
    // Return a new stream when |pathname| points to a directory so that our
    // OnDirectoryContentsNeeded() is called back from stream->getdents().
    ALOG_ASSERT(
        EndsWith(stream->GetStreamType(), "_dir", true),  // sanity check
        "pathname=%s, oflag=%d", pathname.c_str(), oflag);
    return new DirectoryFileStream("redirect", stream->pathname(), this);
  }
  return stream;
}

Dir* RedirectHandler::OnDirectoryContentsNeeded(const std::string& name) {
  Dir* dir = underlying_->OnDirectoryContentsNeeded(name);
  if (dir) {
    base::hash_map<std::string, std::vector<std::string> >::const_iterator it =
        dir_to_symlinks_.find(name);
    if (it != dir_to_symlinks_.end()) {
      for (size_t i = 0; i < it->second.size(); ++i)
        dir->Add(it->second[i], Dir::SYMLINK);
    }
  }
  return dir;
}

ssize_t RedirectHandler::readlink(const std::string& pathname,
                                  std::string* resolved) {
  const std::string rewritten = GetSymlinkTarget(pathname);
  if (rewritten.empty()) {
    // Not a link.
    errno = EINVAL;
    return -1;
  }
  *resolved = rewritten;
  return resolved->size();
}

int RedirectHandler::remove(const std::string& pathname) {
  // Note: Currently, removing, renaming, or unlinking the symbolic link itself
  // it not supported since our code does not do that at all (and we cannot
  // support removing symlinks in the readonly file image anyway). If you really
  // need to support it, you can modify VFS so that VFS calls these methods with
  // the symbolic link path name itself.
  return underlying_->remove(pathname);
}

int RedirectHandler::rename(const std::string& oldpath,
                            const std::string& newpath) {
  // See the comment in remove().
  return underlying_->rename(oldpath, newpath);
}

int RedirectHandler::rmdir(const std::string& pathname) {
  // See the comment in remove(). When the |pathname| is a symbolic link itself,
  // this method thouls return ENOTDIR.
  return underlying_->rmdir(pathname);
}

int RedirectHandler::stat(const std::string& pathname, struct stat* out) {
  return underlying_->stat(pathname, out);
}

int RedirectHandler::statfs(const std::string& pathname, struct statfs* out) {
  return underlying_->statfs(pathname, out);
}

int RedirectHandler::symlink(const std::string& oldpath,
                             const std::string& newpath) {
  struct stat st;
  // Save errno because it can be changed by stat below.
  int old_errno = errno;
  if (!GetSymlinkTarget(newpath).empty() || !underlying_->stat(newpath, &st)) {
    errno = EEXIST;
    return -1;
  }
  errno = old_errno;
  AddSymlink(oldpath, newpath);
  return 0;
}

int RedirectHandler::truncate(const std::string& pathname, off64_t length) {
  return underlying_->truncate(pathname, length);
}

int RedirectHandler::unlink(const std::string& pathname) {
  // See the comment in remove().
  return underlying_->unlink(pathname);
}

int RedirectHandler::utimes(const std::string& pathname,
                            const struct timeval times[2]) {
  return underlying_->utimes(pathname, times);
}

void RedirectHandler::AddSymlink(const std::string& dest,
                                 const std::string& src) {
  ALOG_ASSERT(!util::EndsWithSlash(src));

  const bool result = symlinks_.insert(std::make_pair(src, dest)).second;
  ALOG_ASSERT(result, "Failed to add a symbolic link: %s -> %s",
              src.c_str(), dest.c_str());

  const std::string dir_name = util::GetDirName(src);
  const std::string link_name = arc::GetBaseName(src.c_str());
  ALOG_ASSERT(!dir_name.empty(), "src=%s", src.c_str());
  ALOG_ASSERT(!link_name.empty(), "src=%s", src.c_str());

  dir_to_symlinks_[dir_name].push_back(link_name);
}

std::string RedirectHandler::GetSymlinkTarget(const std::string& src) const {
  base::hash_map<std::string, std::string>::const_iterator it =  // NOLINT
      symlinks_.find(src);
  if (it == symlinks_.end())
    return std::string();
  return it->second;
}

}  // namespace posix_translation
