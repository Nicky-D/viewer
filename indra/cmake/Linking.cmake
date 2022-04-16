# -*- cmake -*-

include_guard()
include(Variables)

set(ARCH_PREBUILT_DIRS ${AUTOBUILD_INSTALL_DIR}/lib)
set(ARCH_PREBUILT_DIRS_PLUGINS ${AUTOBUILD_INSTALL_DIR}/plugins)
set(ARCH_PREBUILT_DIRS_RELEASE ${AUTOBUILD_INSTALL_DIR}/lib/release)
set(ARCH_PREBUILT_DIRS_DEBUG ${AUTOBUILD_INSTALL_DIR}/lib/debug)
if (WINDOWS)
  set(SHARED_LIB_STAGING_DIR ${CMAKE_BINARY_DIR}/sharedlibs)
  set(EXE_STAGING_DIR ${CMAKE_BINARY_DIR}/sharedlibs)
elseif (LINUX)
  set(SHARED_LIB_STAGING_DIR ${CMAKE_BINARY_DIR}/sharedlibs/lib)
  set(EXE_STAGING_DIR ${CMAKE_BINARY_DIR}/sharedlibs/bin)
elseif (DARWIN)
  set(SHARED_LIB_STAGING_DIR ${CMAKE_BINARY_DIR}/sharedlibs)
  set(EXE_STAGING_DIR "${CMAKE_BINARY_DIR}/sharedlibs")
  if( ${CMAKE_GENERATOR} STREQUAL "Ninja")
    set(EXE_STAGING_DIR "${CMAKE_BINARY_DIR}/sharedlibs/${CMAKE_BUILD_TYPE} ")
  else()
    set(EXE_STAGING_DIR "${CMAKE_BINARY_DIR}/sharedlibs")
  endif()
endif (WINDOWS)

# Autobuild packages must provide 'release' versions of libraries, but may provide versions for
# specific build types.  AUTOBUILD_LIBS_INSTALL_DIRS lists first the build type directory and then
# the 'release' directory (as a default fallback).
# *NOTE - we have to take special care to use CMAKE_CFG_INTDIR on IDE generators (like mac and
# windows) and CMAKE_BUILD_TYPE on Makefile based generators (like linux).  The reason for this is
# that CMAKE_BUILD_TYPE is essentially meaningless at configuration time for IDE generators and
# CMAKE_CFG_INTDIR is meaningless at build time for Makefile generators
if(WINDOWS OR DARWIN)
  # the cmake xcode and VS generators implicitly append ${CMAKE_CFG_INTDIR} to the library paths for us
  # fortunately both windows and darwin are case insensitive filesystems so this works.
  # Ninja on the other hand needs the the full path
  if( ${CMAKE_GENERATOR} STREQUAL "Ninja")
    string(TOLOWER ${CMAKE_BUILD_TYPE} CMAKE_BUILD_TYPE_LOWER)
    set(AUTOBUILD_LIBS_INSTALL_DIRS ${AUTOBUILD_INSTALL_DIR}/lib/${CMAKE_BUILD_TYPE_LOWER})
  else()
    set(AUTOBUILD_LIBS_INSTALL_DIRS "${AUTOBUILD_INSTALL_DIR}/lib/")
  endif()
else(WINDOWS OR DARWIN)
  # else block is for linux and any other makefile based generators
  string(TOLOWER ${CMAKE_BUILD_TYPE} CMAKE_BUILD_TYPE_LOWER)
  set(AUTOBUILD_LIBS_INSTALL_DIRS ${AUTOBUILD_INSTALL_DIR}/lib/${CMAKE_BUILD_TYPE_LOWER})
endif(WINDOWS OR DARWIN)

if (NOT "${CMAKE_BUILD_TYPE}" STREQUAL "Release")
  # When we're building something other than Release, append the
  # packages/lib/release directory to deal with autobuild packages that don't
  # provide (e.g.) lib/debug libraries.
  list(APPEND AUTOBUILD_LIBS_INSTALL_DIRS ${ARCH_PREBUILT_DIRS_RELEASE})
endif (NOT "${CMAKE_BUILD_TYPE}" STREQUAL "Release")

link_directories(${AUTOBUILD_LIBS_INSTALL_DIRS})

create_target(ll::oslibraries)

if (LINUX)
  set_target_libraries( ll::oslibraries
          dl
          pthread
          rt)
elseif (WINDOWS)
  set_target_libraries( ll::oslibraries
          advapi32
          shell32
          ws2_32
          mswsock
          psapi
          winmm
          netapi32
          wldap32
          gdi32
          user32
          ole32
          dbghelp
          legacy_stdio_definitions
          )
else()
  include(CMakeFindFrameworks)
  find_library(COREFOUNDATION_LIBRARY CoreFoundation)
  find_library(CARBON_LIBRARY Carbon)
  find_library(COCOA_LIBRARY Cocoa)
  find_library(IOKIT_LIBRARY IOKit)

  find_library(AGL_LIBRARY AGL)
  find_library(APPKIT_LIBRARY AppKit)
  find_library(COREAUDIO_LIBRARY CoreAudio)

  set_target_libraries( ll::oslibraries
          ${COCOA_LIBRARY}
          ${IOKIT_LIBRARY}
          ${COREFOUNDATION_LIBRARY}
          ${CARBON_LIBRARY}
          ${AGL_LIBRARY}
          ${APPKIT_LIBRARY}
          ${COREAUDIO_LIBRARY}
          )
endif()



