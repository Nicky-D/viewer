#ifndef LINUX_WINDOWS_IMPL_H
#define LINUX_WINDOWS_IMPL_H

enum class EDisplayServer
{
    eUnknown,
    eX11,
    eWayland,
};

class WindowImpl
{
public:
    virtual void initialize(SDL_SysWMinfo const&, SDL_Window *) = 0;
    virtual void setMinSize(U32 min_width, U32 min_height) = 0;

    virtual void sync() = 0;
    virtual void startFlashing( F32 seconds ) = 0;
    virtual void stopFlashingIfExpired() = 0;

    virtual bool captureInput( bool grabInput ) = 0;

    virtual void bringToFront() = 0;

    static WindowImpl* create( EDisplayServer );
};


#endif