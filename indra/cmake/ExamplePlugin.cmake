# -*- cmake -*-
include(Linking)
include(Prebuilt)

set(EXAMPLEPLUGIN ON CACHE BOOL
        "EXAMPLEPLUGIN support for the llplugin/llmedia test apps.")

if (WINDOWS)
elseif (DARWIN)
elseif (LINUX)
endif (WINDOWS)
