include_guard()
include(FetchContent)

# Only available with cmake > 3.24.0
# sets DOWNLOAD_EXTRACT_TIMESTAMP to FALSE, setting the timestamp of extracted files to time
# of extraction rather than using the time that is recorded in the archive
if( POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

if( USE_SYSROOT )
  set( SYSROOT_NAME prebuild_files )
  if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
	FetchContent_Declare( ${SYSROOT_NAME}
	  URL https://github.com/slviewer-3p/_build-all/releases/download/v0.11-DRTVWR-559/sysroot.tar.xz
	  URL_HASH MD5=9a1c678f7e754faab8755749e7549777
	  )
  endif()
  FetchContent_MakeAvailable( ${SYSROOT_NAME} )

  function (use_prebuilt_binary _binary)
  endfunction()
endif()
