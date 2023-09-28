# -*- cmake -*-

include(Variables)
include(GLEXT)
include(Prebuilt)

include_guard()
add_library( ll::SDL INTERFACE IMPORTED )


if (LINUX)
  #Must come first as use_system_binary can exit this file early

  if( USE_SD2 )
    target_compile_definitions( ll::SDL INTERFACE LL_SDL=1 LL_SDL_VERSION=2 )
    set( SDL_VERSION SDL3 )
    set( SDL_VERSION_LOWERCASE sdl3 )
  else()
    target_compile_definitions( ll::SDL INTERFACE LL_SDL=1 LL_SDL_VERSION=3 )
    set( SDL_VERSION SDL3 )
    set( SDL_VERSION_LOWERCASE sdl3 )
  endif()

  use_system_binary(SDL)
  use_prebuilt_binary(SDL)
  
  target_include_directories( ll::SDL SYSTEM INTERFACE ${LIBS_PREBUILT_DIR}/include)
  target_link_libraries( ll::SDL INTERFACE ${SDL_VERSION} X11)
endif (LINUX)


