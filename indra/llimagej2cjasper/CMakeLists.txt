# -*- cmake -*-

project(llimagej2jasper)

include(00-Common)
include(LLCommon)
include(LLImage)
include(JasPer)

add_library (llimagej2cjasper
  llimagej2cjasper.cpp
  llimagej2cjasper.cpp
  CMakeLists.txt )

target_link_libraries( llimagej2cjasper FV::jasper llimage llcommon )

