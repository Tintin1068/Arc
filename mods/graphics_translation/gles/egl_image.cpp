/*
 * Copyright (C) 2011 The Android Open Source Project
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
#include "graphics_translation/gles/egl_image.h"

#include <GLES/gl.h>

#include "common/alog.h"
#include "graphics_translation/gles/gles_context.h"
#include "graphics_translation/gles/texture_data.h"

GlesContext* GetCurrentGlesContext();

EglImage::EglImage(GLenum global_texture_target, GLuint global_texture_name,
                   const TextureDataPtr& texture)
  : width(texture->GetWidth()),
    height(texture->GetHeight()),
    format(texture->GetFormat()),
    global_texture_target(global_texture_target),
    global_texture_name(global_texture_name) {
}

EglImagePtr EglImage::Create(GLenum global_target, GLuint name) {
  GlesContext* c = GetCurrentGlesContext();
  if (!c) {
    return EglImagePtr();
  }

  ShareGroupPtr sg = c->GetShareGroup();
  TextureDataPtr tex = sg->GetTextureData(name);
  if (!tex || tex->GetWidth() == 0 || tex->GetHeight() == 0) {
    LOG_ALWAYS_FATAL("No such texture: %d", name);
    return EglImagePtr();
  }

  const GLuint global_name = sg->GetTextureGlobalName(name);
  return EglImagePtr(new EglImage(global_target, global_name, tex));
}
