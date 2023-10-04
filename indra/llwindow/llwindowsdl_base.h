#ifndef LL_WINDOW_SDL_BASE_H
#define LL_WINDOW_SDL_BASE_H

#include "llwindow.h"
#include "lltimer.h"
// AssertMacros.h does bad things.
#include "fix_macros.h"
#undef verify
#undef require

#include "ndGPUInfo.h"

class LLWindowSDLBase: public LLWindow
{
    ndgpuinfo::gpu_info *mGPUInfo = nullptr;
protected:
    LLWindowSDLBase(LLWindowCallbacks* callbacks, BOOL fullscreen, U32 flags)
    : LLWindow(callbacks, fullscreen, flags)
    {
        mGPUInfo = ndgpuinfo::init();
    }

    uint64_t  getVRAM() const
    {
        llassert_always(mGPUInfo);
        return getTotalMemory(mGPUInfo);
    }
};

#endif
