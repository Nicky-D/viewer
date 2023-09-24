# -*- cmake -*-

include_guard()

include(Prebuilt)
include(GLIB)

add_library( ll::gstreamer10 INTERFACE IMPORTED )

if (USESYSTEMLIBS)
  include(FindPkgConfig)

  pkg_check_modules(GSTREAMER10 REQUIRED gstreamer-1.0)
  pkg_check_modules(GSTREAMER10_PLUGINS_BASE REQUIRED gstreamer-plugins-base-1.0)
elseif (LINUX OR WINDOWS)
  use_prebuilt_binary(gstreamer10)
  use_prebuilt_binary(libxml2)

  target_include_directories( ll::gstreamer10 SYSTEM INTERFACE ${LIBS_PREBUILT_DIR}/include/gstreamer-1.0)
  target_link_libraries( ll::gstreamer10 INTERFACE  ll::glib_headers)

endif (USESYSTEMLIBS)

if (GSTREAMER10_FOUND AND GSTREAMER10_PLUGINS_BASE_FOUND)
  set(GSTREAMER10 ON CACHE BOOL "Build with GStreamer-1.0 streaming media support.")
endif (GSTREAMER10_FOUND AND GSTREAMER10_PLUGINS_BASE_FOUND)

if (GSTREAMER10)
  add_definitions(-DLL_GSTREAMER10_ENABLED=1)
endif (GSTREAMER10)
