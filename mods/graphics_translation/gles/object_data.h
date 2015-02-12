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
#ifndef GRAPHICS_TRANSLATION_GLES_OBJECT_DATA_H_
#define GRAPHICS_TRANSLATION_GLES_OBJECT_DATA_H_

#include "graphics_translation/gles/smartptr.h"

// The global name is the name generated by the underlying GL implementation
// (eg. Pepper Graphics, GLX, etc.)
typedef uint32_t ObjectGlobalName;

// The local name is the name that can be used by the client to reference GL
// objects.
typedef uint32_t ObjectLocalName;

// The different GL object types.
enum ObjectType {
  BUFFER,
  FRAMEBUFFER,
  RENDERBUFFER,
  TEXTURE,
  VERTEX_SHADER,
  FRAGMENT_SHADER,
  PROGRAM,
  NUM_OBJECT_TYPES,

  // Shaders are a bit special in that both vertex shaders and fragment shaders
  // are both considered Shader objects.
  SHADER = VERTEX_SHADER
};

// The base class for GL object wrappers.
class ObjectData {
 public:
  explicit ObjectData(ObjectType type)
    : type_(type),
      local_name_(0) {
  }

  ObjectData(ObjectType type, ObjectLocalName name)
    : type_(type),
      local_name_(name) {
  }

  virtual ~ObjectData() {
  }

  ObjectType GetDataType() const {
    return type_;
  }

  ObjectLocalName GetLocalName() const {
    return local_name_;
  }

 private:
  ObjectType type_;
  ObjectLocalName local_name_;

  ObjectData(const ObjectData&);
  ObjectData& operator=(const ObjectData&);
};

typedef SmartPtr<ObjectData> ObjectDataPtr;

#endif  // GRAPHICS_TRANSLATION_GLES_OBJECT_DATA_H_
