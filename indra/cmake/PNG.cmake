# -*- cmake -*-
include(Prebuilt)

if( TARGET libpng::libpng )
  return()
endif()
create_target(libpng::libpng)

use_prebuilt_binary(libpng)
if (WINDOWS)
  set_target_libraries(libpng::libpng libpng16)
else()
  set_target_libraries(libpng::libpng png16 )
endif()
set_target_include_dirs( libpng::libpng ${LIBS_PREBUILT_DIR}/include/libpng16)
