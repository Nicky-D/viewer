# -*- cmake -*-
include(Prebuilt)

include_guard()
add_library( ll::freetype INTERFACE IMPORTED )

# Use the system one on Linux
if(LINUX)
  find_package(Freetype REQUIRED)
  target_include_directories(ll::freetype SYSTEM INTERFACE ${FREETYPE_INCLUDE_DIRS})
  target_link_libraries( ll::freetype INTERFACE ${FREETYPE_LIBRARIES} )
else()
  use_system_binary(freetype)
  use_prebuilt_binary(freetype)
  target_include_directories( ll::freetype SYSTEM INTERFACE  ${LIBS_PREBUILT_DIR}/include/freetype2/)
  target_link_libraries( ll::freetype INTERFACE freetype )
endif()

