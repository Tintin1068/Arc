/*
 * Copyright (C) 2008 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifndef GRAPHICS_TRANSLATION_GRALLOC_GRAPHICS_BUFFER_H_
#define GRAPHICS_TRANSLATION_GRALLOC_GRAPHICS_BUFFER_H_

#include "cutils/native_handle.h"
#include "sys/types.h"

struct GraphicsBuffer : public native_handle {
  // Magic value used to verify validity of the color buffer handle.
  enum {
    kMagicValue = 0x0bfabfab
  };

  GraphicsBuffer(size_t size, int usage, int width, int height, int format,
                 int gl_format, int gl_type);

  ~GraphicsBuffer();

  // Check if graphics buffer is valid.
  bool IsValid() const;

  // Acquire/release references to underlying resources.
  int Acquire();
  int Release();

  // Lock/unlock graphics buffer for sw usage.
  int Lock(int usage, int left, int top, int width, int height, void** vaddr);
  int Unlock();

  // Draw contents of color buffer and swap.
  int Post();

  void SetSystemTexture(int target, int name);
  void ClearSystemTexture();
  void SetObjectTrackingHandle(int handle);

  int GetHostTarget() const;
  int GetHostTexture() const;
  void* GetHostContext() const;

  int GetUsage() const { return usage_; }
  int GetWidth() const { return width_; }
  int GetHeight() const { return height_; }
  int GetFormat() const { return format_; }

  void* GetHostHandle() const { return hw_handle_; }

 private:
  static int GetVersion();
  static int CalculateNumInts(int numFds);

  bool CanBePosted() const;

  int fd_;           // Will be -1 if buffer not allocated (ie. no SW access).
                     // Must be the first member (required by native_handle).
  int magic_;        // Magic number to validate handle.
  int usage_;        // Buffer usage flags.
  int width_;        // Buffer width.
  int height_;       // Buffer height.
  int format_;       // Internal pixel format.
  int gl_format_;    // OpenGL format enum used for h/w color buffer.
  int gl_type_;      // OpenGL type enum used for h/w color buffer.
  int locked_left_;  // Region of buffer locked for s/w write.
  int locked_top_;
  int locked_width_;
  int locked_height_;
  int system_texture_;
  int system_target_;
  int system_texture_tracking_handle_;
  size_t sw_buffer_size_;  // Size of s/w image buffer.
  char* sw_buffer_;        // Pointer to s/w image buffer.
  void* hw_handle_;        // Handle to underlying h/w color buffer.
  char* locked_addr_;

  GraphicsBuffer(const GraphicsBuffer&);
  GraphicsBuffer& operator=(const GraphicsBuffer&);
};

#endif  // GRAPHICS_TRANSLATION_GRALLOC_GRAPHICS_BUFFER_H_
