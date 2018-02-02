# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from src.build.util import download_package_util


def check_and_perform_updates(cache_base_path, cache_history_size):
  download_package_util.BasicCachedPackage(
      'src/build/DEPS.naclports-python',
      'out/naclports-python',
      cache_base_path=cache_base_path,
      cache_history_size=cache_history_size,
      download_method=download_package_util.gsutil_download_url()
  ).check_and_perform_update()
