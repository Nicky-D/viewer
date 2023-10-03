# include <unistd.h>
# include <sys/types.h>
# include <sys/wait.h>
# include <stdio.h>

# include <X11/Xutil.h>

class X11Window: public WindowImpl
{
    bool mFlashing = false;
    LLTimer mFlashTimer;

    Window mSDL_XWindowID = None;
    Display *mSDL_Display = nullptr;
    void x11_set_urgent(bool urgent);

public:
    void initialize(SDL_SysWMinfo const&, SDL_Window *);
    void setMinSize(U32 min_width, U32 min_height);

    void sync();
    void startFlashing( F32 seconds );
    void stopFlashingIfExpired();

    bool captureInput( bool grabInput );

    void bringToFront();
};

class SDLWindow: public WindowImpl
{
    bool mFlashing = false;
    LLTimer mFlashTimer;

    SDL_Window *mWindow = nullptr;
public:
    void initialize(SDL_SysWMinfo const&, SDL_Window *aWindow )
    {
        mWindow = aWindow;
    }

    void setMinSize(U32 min_width, U32 min_height) {}

    void sync() {}
    void startFlashing( F32 seconds );
    void stopFlashingIfExpired();

    bool captureInput( bool grabInput ) {}
    void bringToFront() {}
};

WindowImpl* WindowImpl::create( EDisplayServer aServer )
{
    switch( aServer )
    {
        case( EDisplayServer::eWayland ):
            return new SDLWindow();
        case( EDisplayServer::eX11 ):
            return  new X11Window();
        default:
            return new SDLWindow();
    }
};

void X11Window::initialize(const SDL_SysWMinfo &info,SDL_Window *a)
{
    mSDL_Display = info.info.x11.display;
    mSDL_XWindowID = info.info.x11.window;
}

void X11Window::setMinSize( U32 min_width, U32 min_height )
{
    // Set the minimum size limits for X11 window
    // so the window manager doesn't allow resizing below those limits.
    XSizeHints* hints = XAllocSizeHints();
    hints->flags |= PMinSize;
    hints->min_width = min_width;
    hints->min_height = min_height;

    XSetWMNormalHints(mSDL_Display, mSDL_XWindowID, hints);

    XFree(hints);
}

void X11Window::sync()
{
    if (mSDL_Display)
    {
        // Everything that we/SDL asked for should happen before we
        // potentially hand control over to GTK.
        maybe_lock_display();
        XSync(mSDL_Display, False);
        maybe_unlock_display();
    }
}

void X11Window::startFlashing( F32 seconds )
{
    F32 remaining_time = mFlashTimer.getRemainingTimeF32();
    if (remaining_time < seconds)
        remaining_time = seconds;
    mFlashTimer.reset();
    mFlashTimer.setTimerExpirySec(remaining_time);

    x11_set_urgent(true);
    mFlashing = true;
}

void X11Window::stopFlashingIfExpired()
{
    if (mFlashing && mFlashTimer.hasExpired())
    {
        x11_set_urgent(false);
        mFlashing = false;
    }
}

void X11Window::x11_set_urgent(bool urgent)
{
    if (mSDL_Display)
    {
        XWMHints *wm_hints;

        LL_INFOS() << "X11 hint for urgency, " << urgent << LL_ENDL;

        maybe_lock_display();
        wm_hints = XGetWMHints(mSDL_Display, mSDL_XWindowID);
        if (!wm_hints)
            wm_hints = XAllocWMHints();

        if (urgent)
            wm_hints->flags |= XUrgencyHint;
        else
            wm_hints->flags &= ~XUrgencyHint;

        XSetWMHints(mSDL_Display, mSDL_XWindowID, wm_hints);
        XFree(wm_hints);
        XSync(mSDL_Display, False);
        maybe_unlock_display();
    }
}

bool X11Window::captureInput(bool grabInput)
{
    bool newGrab = grabInput;

    if (mSDL_Display)
    {
        /* we dirtily mix raw X11 with SDL so that our pointer
           isn't (as often) constrained to the limits of the
           window while grabbed, which feels nicer and
           hopefully eliminates some reported 'sticky pointer'
           problems.  We use raw X11 instead of
           SDL_WM_GrabInput() because the latter constrains
           the pointer to the window and also steals all
           *keyboard* input from the window manager, which was
           frustrating users. */
        int result;
        if (grabInput)
        {
            maybe_lock_display();
            result = XGrabPointer(mSDL_Display, mSDL_XWindowID,
                                  True, 0, GrabModeAsync,
                                  GrabModeAsync,
                                  None, None, CurrentTime);
            maybe_unlock_display();
            if (GrabSuccess == result)
                newGrab = true;
            else
                newGrab = false;
        }
        else
        {
            newGrab = false;

            maybe_lock_display();
            XUngrabPointer(mSDL_Display, CurrentTime);
            // Make sure the ungrab happens RIGHT NOW.
            XSync(mSDL_Display, False);
            maybe_unlock_display();
        }
    }

    return newGrab;
}

void X11Window::bringToFront()
{
    if (mSDL_Display)
    {
        maybe_lock_display();
        XRaiseWindow(mSDL_Display, mSDL_XWindowID);
        XSync(mSDL_Display, False);
        maybe_unlock_display();
    }
}

void SDLWindow::startFlashing(F32 seconds)
{
    F32 remaining_time = mFlashTimer.getRemainingTimeF32();
    if (remaining_time < seconds)
        remaining_time = seconds;
    mFlashTimer.reset();
    mFlashTimer.setTimerExpirySec(remaining_time);

    SDL_FlashWindow( mWindow, SDL_FLASH_UNTIL_FOCUSED);

    mFlashing = true;
}
void SDLWindow::stopFlashingIfExpired()
{
    if (mFlashing && mFlashTimer.hasExpired())
    {
        SDL_FlashWindow( mWindow, SDL_FLASH_CANCEL);
        mFlashing = false;
    }
}
