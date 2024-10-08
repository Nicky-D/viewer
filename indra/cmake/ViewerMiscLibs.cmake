# -*- cmake -*-
include(Prebuilt)

if (LINUX)
  #use_prebuilt_binary(libuuid)
  add_library( ll::fontconfig INTERFACE IMPORTED )

  if( NOT USE_CONAN )
    find_package(Fontconfig REQUIRED)
    target_include_directories( ll::fontconfig SYSTEM INTERFACE ${Fontconfig_INCLUDE_DIRS})
    target_link_libraries( ll::fontconfig INTERFACE ${Fontconfig_LIBRARIES})
  else()
    target_link_libraries( ll::fontconfig INTERFACE CONAN_PKG::fontconfig )
  endif()
endif (LINUX)

if( NOT USE_CONAN )
  use_prebuilt_binary(libhunspell)
endif()

use_prebuilt_binary(slvoice)

