#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Syncs the nacl sdk at a pinned version given in NACLSDK.json

import argparse
import filecmp
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib

import build_common
from util import file_util


_ROOT_DIR = build_common.get_arc_root()
_NACL_SDK_DIR = os.path.join(_ROOT_DIR, 'third_party', 'nacl_sdk')
_STAMP_PATH = os.path.join(_NACL_SDK_DIR, 'STAMP')
_PINNED_MANIFEST = os.path.join(_ROOT_DIR, 'src', 'build', 'DEPS.naclsdk')
_NACL_MIRROR = 'https://commondatastorage.googleapis.com/nativeclient-mirror'
_LATEST_MANIFEST_URL = _NACL_MIRROR + '/nacl/nacl_sdk/naclsdk_manifest2.json'
_NACL_SDK_ZIP_URL = _NACL_MIRROR + '/nacl/nacl_sdk/nacl_sdk.zip'


def _log_check_call(log_function, *args, **kwargs):
  """Log each line of output from a command.

  Args:
    log_function: Function to call to log.
    *args: Ordered args.
    **kwargs: Keyword args.
  """
  p = subprocess.Popen(
      *args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
  for line in p.stdout:
    log_function(line.rstrip())
  return_code = p.wait()
  if return_code:
    # Unlike subprocess.check_call, as we do not use 'args' kw-arg in this
    # module, we do not check it.
    cmd = args[0]
    raise subprocess.CalledProcessError(return_code, cmd)


def _roll_forward_pinned_manifest():
  """Roll forward the pinned manifest to the latest version."""
  logging.info('Rolling forward the pinned NaCl manifest...')

  @build_common.with_retry_on_exception
  def retrieve_manifest():
    urllib.urlretrieve(_LATEST_MANIFEST_URL, _PINNED_MANIFEST)
  retrieve_manifest()
  logging.info('Done.')


def _should_delete_nacl_sdk():
  """Returns True if the SDK tree should be deleted."""
  if not os.path.exists(_STAMP_PATH):
    return False
  # Returns true if _PINNED_MANIFEST is modified. This is necessary because
  # './naclsdk update' does nothing when _PINNED_MANIFEST is reverted back
  # to an older revision. We use filecmp.cmp() rather than parsing the manifest
  # file. Since deleting the SDK is relatively cheap, and updating the SDK is
  # as slow as installing it from scratch, just comparing files would be okay.
  return not filecmp.cmp(_PINNED_MANIFEST, _STAMP_PATH)


def _ensure_naclsdk_downloaded():
  """Downloads the naclsdk script if necessary."""
  if (not _should_delete_nacl_sdk() and
      os.path.exists(os.path.join(_NACL_SDK_DIR, 'naclsdk'))):
    return

  # Deleting the obsolete SDK tree usually takes only <1s.
  logging.info('Deleting old NaCl SDK...')
  shutil.rmtree(_NACL_SDK_DIR, ignore_errors=True)

  # Download sdk zip if needed. The zip file only contains a set of Python
  # scripts that download the actual SDK. This step usually takes only <1s.
  logging.info('Downloading nacl_sdk.zip...')
  zip_content = build_common.download_content(_NACL_SDK_ZIP_URL)
  # The archived path starts with nacl_sdk/, so we inflate the contents
  # into the one level higher directory.
  file_util.inflate_zip(zip_content, os.path.dirname(_NACL_SDK_DIR))
  os.chmod(os.path.join(_NACL_SDK_DIR, 'naclsdk'), 0700)


def _update_nacl_sdk():
  """Syncs the NaCL SDK. based on pinned manifest."""

  # In ./naclsdk execution, it sometimes fails due to the server-side or
  # network errors. So, here we retry on failure sometimes.
  @build_common.with_retry_on_exception
  def internal():
    start = time.time()
    logging.info('Updating NaCl SDK...')
    _log_check_call(
        logging.info,
        ['./naclsdk', 'update', '-U', 'file://' + _PINNED_MANIFEST,
         '--force', 'pepper_canary'],
        cwd=_NACL_SDK_DIR)
    elapsed_time = time.time() - start
    if elapsed_time > 1:
      print 'NaCl SDK update took %0.3fs' % elapsed_time
    logging.info('Done. [%fs]' % elapsed_time)
  return internal()


def _update_stamp():
  """Update a stamp file for build tracking."""
  shutil.copyfile(_PINNED_MANIFEST, _STAMP_PATH)


def main(args):
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='store_true', help='Emit '
                      'verbose output.')
  parser.add_argument('-r', '--roll-forward', dest='roll', action='store_true',
                      help='Update pinned NaCl SDK manifest version to the '
                      'latest..')
  args = parser.parse_args(args)

  if args.verbose:
    level = logging.DEBUG
  else:
    level = logging.WARNING
  logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

  if args.roll:
    _roll_forward_pinned_manifest()

  _ensure_naclsdk_downloaded()
  _update_nacl_sdk()
  _update_stamp()


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
