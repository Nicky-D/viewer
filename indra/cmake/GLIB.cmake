include_guard()

include(Prebuilt)

add_library( ll::glib INTERFACE IMPORTED )
add_library( ll::glib_headers INTERFACE IMPORTED )
add_library( ll::gio INTERFACE IMPORTED )

if( LINUX )
  use_prebuilt_binary(glib)

  target_include_directories( ll::glib SYSTEM INTERFACE ${LIBS_PREBUILT_DIR}/include/glib-2.0 ${LIBS_PREBUILT_DIR}/lib/release/glib-2.0/include  )
  target_link_libraries( ll::glib INTERFACE libgobject-2.0.a libglib-2.0.a libffi.a libpcre.a )
  target_compile_definitions( ll::glib INTERFACE -DLL_GLIB=1)

  target_include_directories( ll::glib_headers SYSTEM INTERFACE ${LIBS_PREBUILT_DIR}/include/glib-2.0 ${LIBS_PREBUILT_DIR}/lib/release/glib-2.0/include  )
  target_compile_definitions( ll::glib_headers INTERFACE -DLL_GLIB=1)


  target_link_libraries( ll::gio INTERFACE  libgio-2.0.a libgmodule-2.0.a -lresolv ll::glib  )

endif()
