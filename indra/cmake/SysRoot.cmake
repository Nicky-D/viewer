include_guard()
include(FetchContent)

if( USE_SYSROOT )
  set( SYSROOT_NAME prebuild_files )
  if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
	FetchContent_Declare( ${SYSROOT_NAME}
	  URL https://github.com/slviewer-3p/_build-all/releases/download/v0.1-DRTVWR-559/sysroot-DRTVWR-559.tar.bz2
	  URL_HASH MD5=ab9cd51d637ac458fe198552ef20e2c3
	  DOWNLOAD_NO_PROGRESS ON
	  )
  endif()
  FetchContent_MakeAvailable( ${SYSROOT_NAME} )

  function (use_prebuilt_binary _binary)
  endfunction()
endif()

