# include <unistd.h>
# include <sys/types.h>
# include <sys/wait.h>
# include <stdio.h>

# include <X11/Xutil.h>

class X11Clipboard: public ClipboardImpl
{
    bool getSelectionText( Atom selection, Atom type, LLWString &text );

    Window mSDL_XWindowID = None;
    Display *mSDL_Display = nullptr;

    std::array<Atom, 3> gSupportedAtoms;

    Atom XA_CLIPBOARD;
    Atom XA_TARGETS;
    Atom PVT_PASTE_BUFFER;
    long const MAX_PASTE_BUFFER_SIZE = 16383;

    void filterSelectionRequest( XEvent aEvent );
    void filterSelectionClearRequest( XEvent aEvent );
    static int x11_clipboard_filter(void*, SDL_Event *evt);
    bool grab_property(Display* display, Window window, Atom selection, Atom target);

public:
    void initialize(SDL_SysWMinfo const&);

    bool hasClipboardText();

    bool getSelectionText(bool primary, LLWString& text);
    bool setSelectionText(bool primary, const LLWString& text);

};

class SDLClipboard: public ClipboardImpl
{
    void initialize(SDL_SysWMinfo const &) {}

    bool hasClipboardText();

    bool getSelectionText(bool primary, LLWString &text);
    bool setSelectionText(bool primary, const LLWString &text);
};

ClipboardImpl* ClipboardImpl::create( EDisplayServer aServer )
{
    switch( aServer )
    {
        case( EDisplayServer::eWayland ):
            return new SDLClipboard();
        case( EDisplayServer::eX11 ):
            return  new X11Clipboard();
        default:
            return new SDLClipboard();
    }
};

void X11Clipboard::filterSelectionRequest(XEvent aEvent)
{
    auto *display = mSDL_Display;
    auto &request = aEvent.xselectionrequest;

    XSelectionEvent reply { SelectionNotify, aEvent.xany.serial, aEvent.xany.send_event, display,
                            request.requestor, request.selection, request.target,
                            request.property,request.time };

    if (request.target == XA_TARGETS)
    {
        XChangeProperty(display, request.requestor, request.property,
                        XA_ATOM, 32, PropModeReplace,
                        (unsigned char *) &gSupportedAtoms.front(), gSupportedAtoms.size());
    }
    else if (std::find(gSupportedAtoms.begin(), gSupportedAtoms.end(), request.target) !=
             gSupportedAtoms.end())
    {
        std::string utf8;
        if (request.selection == XA_PRIMARY)
            utf8 = wstring_to_utf8str(gWindowImplementation->getPrimaryText());
        else
            utf8 = wstring_to_utf8str(gWindowImplementation->getSecondaryText());

        XChangeProperty(display, request.requestor, request.property,
                        request.target, 8, PropModeReplace,
                        (unsigned char *) utf8.c_str(), utf8.length());
    }
    else if (request.selection == XA_CLIPBOARD)
    {
        // Did not have what they wanted, so no property set
        reply.property = None;
    }
    else
        return;

    XSendEvent(request.display, request.requestor, False, NoEventMask, (XEvent *) &reply);
    XSync(display, False);
}

void X11Clipboard::filterSelectionClearRequest( XEvent aEvent )
{
    auto &request = aEvent.xselectionrequest;
    if (request.selection == XA_PRIMARY)
        gWindowImplementation->clearPrimaryText();
    else if (request.selection == XA_CLIPBOARD)
        gWindowImplementation->clearSecondaryText();
}

int X11Clipboard::x11_clipboard_filter(void *user_date, SDL_Event *evt)
{
    X11Clipboard *pThis = (X11Clipboard*)(user_date);

    Display *display = pThis->mSDL_Display;
    if (!display)
        return 1;

    if (evt->type != SDL_SYSWMEVENT)
        return 1;

    auto xevent = evt->syswm.msg->msg.x11.event;

    if (xevent.type == SelectionRequest)
        pThis->filterSelectionRequest( xevent );
    else if (xevent.type == SelectionClear)
        pThis->filterSelectionClearRequest( xevent );
    return 1;
}

bool X11Clipboard::grab_property(Display* display, Window window, Atom selection, Atom target)
{
    if( !display )
        return false;

    maybe_lock_display();

    XDeleteProperty(display, window, PVT_PASTE_BUFFER);
    XFlush(display);

    XConvertSelection(display, selection, target, PVT_PASTE_BUFFER, window,  CurrentTime);

    // Unlock the connection so that the SDL event loop may function
    maybe_unlock_display();

    const auto start{ SDL_GetTicks() };
    const auto end{ start + 1000 };

    XEvent xevent {};
    bool response = false;

    do
    {
        SDL_Event event {};

        // Wait for an event
        SDL_WaitEvent(&event);

        // If the event is a window manager event
        if (event.type == SDL_SYSWMEVENT)
        {
            xevent = event.syswm.msg->msg.x11.event;

            if (xevent.type == SelectionNotify && xevent.xselection.requestor == window)
                response = true;
        }
    } while (!response && SDL_GetTicks() < end );

    return response && xevent.xselection.property != None;
}

void X11Clipboard::initialize(SDL_SysWMinfo const &info)
{
    mSDL_Display = info.info.x11.display;
    mSDL_XWindowID = info.info.x11.window;

    if (!mSDL_Display)
        return;

    SDL_EventState(SDL_SYSWMEVENT, SDL_ENABLE);
    SDL_SetEventFilter(x11_clipboard_filter, this);

    maybe_lock_display();

    XA_CLIPBOARD = XInternAtom(mSDL_Display, "CLIPBOARD", False);

    gSupportedAtoms[0] = XInternAtom(mSDL_Display, "UTF8_STRING", False);
    gSupportedAtoms[1] = XInternAtom(mSDL_Display, "COMPOUND_TEXT", False);
    gSupportedAtoms[2] = XA_STRING;

    // TARGETS atom
    XA_TARGETS = XInternAtom(mSDL_Display, "TARGETS", False);

    // SL_PASTE_BUFFER atom
    PVT_PASTE_BUFFER = XInternAtom(mSDL_Display, "FS_PASTE_BUFFER", False);

    maybe_unlock_display();
}
bool X11Clipboard::hasClipboardText()
{
    return mSDL_Display && XGetSelectionOwner(mSDL_Display, XA_CLIPBOARD) != None;
}

bool X11Clipboard::getSelectionText( Atom aSelection, Atom aType, LLWString &text )
{
    if( !mSDL_Display )
        return false;

    if( !grab_property(mSDL_Display, mSDL_XWindowID, aSelection,aType ) )
        return false;

    maybe_lock_display();

    Atom type;
    int format{};
    unsigned long len{},remaining {};
    unsigned char* data = nullptr;
    int res = XGetWindowProperty(mSDL_Display, mSDL_XWindowID,
                                 PVT_PASTE_BUFFER, 0, MAX_PASTE_BUFFER_SIZE, False,
                                 AnyPropertyType, &type, &format, &len,
                                 &remaining, &data);
    if (data && len)
    {
        text = LLWString(
                utf8str_to_wstring(reinterpret_cast< char const *>( data ) )
        );
        XFree(data);
    }

    maybe_unlock_display();
    return res == Success;
}

bool X11Clipboard::getSelectionText(bool primary, LLWString& text)
{
    if (!mSDL_Display)
        return false;

    Atom selection = primary?XA_PRIMARY:XA_CLIPBOARD;

    maybe_lock_display();

    Window owner = XGetSelectionOwner(mSDL_Display, selection);
    if (owner == None)
    {
        if (selection == XA_PRIMARY)
        {
            owner = DefaultRootWindow(mSDL_Display);
            selection = XA_CUT_BUFFER0;
        }
        else
        {
            maybe_unlock_display();
            return false;
        }
    }

    maybe_unlock_display();

    for( Atom atom : gSupportedAtoms )
    {
        if(getSelectionText(selection, atom, text ) )
            return true;
    }

    return false;
}

bool X11Clipboard::setSelectionText(bool primary, const LLWString& text)
{
    maybe_lock_display();

    Atom selection = primary?XA_PRIMARY:XA_CLIPBOARD;

    if (selection == XA_PRIMARY)
    {
        std::string utf8 = wstring_to_utf8str(text);
        XStoreBytes(mSDL_Display, utf8.c_str(), utf8.length() + 1);
    }

    XSetSelectionOwner(mSDL_Display, selection, mSDL_XWindowID, CurrentTime);

    auto owner = XGetSelectionOwner(mSDL_Display, selection);

    maybe_unlock_display();

    return owner == mSDL_XWindowID;
}

bool SDLClipboard::hasClipboardText()
{
    return SDL_HasClipboardText();
}
bool SDLClipboard::getSelectionText(bool primary, LLWString &text)
{
#if LL_SDL_VERSION==3
    if( primary)
    {
        char * data = SDL_GetPrimarySelectionText();
        if( !data )
            return false;
        text = utf8str_to_wstring(data);
        SDL_free(data);
        return true;
    }
    else
#endif
    {
        char * data = SDL_GetClipboardText();
        if( !data )
            return false;
        text = utf8str_to_wstring(data);
        SDL_free(data);
    }
}

bool SDLClipboard::setSelectionText(bool primary, const LLWString &text)
{
#if LL_SDL_VERSION==3
    if( primary )
    {
        std::string str = wstring_to_utf8str( text );
        SDL_SetPrimarySelectionText(str.c_str());
    }
    else
#endif
    {
        std::string str = wstring_to_utf8str( text );
        SDL_SetClipboardText(str.c_str());

    }
}