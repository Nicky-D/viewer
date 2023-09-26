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
	  URL https://github.com/Nicky-D/_build-all-3ps/releases/download/v0.23/sysroot-glibc-2.35.tar.xz
	  URL_HASH MD5=8ebe6e9964c8476808fe632c935c5a36
	  )
  endif()
  FetchContent_MakeAvailable( ${SYSROOT_NAME} )
    
  function (use_prebuilt_binary _binary)
  endfunction()
endif()
