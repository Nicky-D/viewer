include_guard()
include(FetchContent)

if( USE_SYSROOT )
  set( SYSROOT_NAME prebuild_files )
  if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
	FetchContent_Declare( ${SYSROOT_NAME}
	  URL https://github.com/slviewer-3p/_build-all/releases/download/v0.8-DRTVWR-559/sysroot.tar.xz
	  URL_HASH MD5=916455868f4803f99155c74203d4d46c
	  DOWNLOAD_NO_PROGRESS ON
	  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
	  )
  endif()
  FetchContent_MakeAvailable( ${SYSROOT_NAME} )

  function (use_prebuilt_binary _binary)
  endfunction()
endif()

