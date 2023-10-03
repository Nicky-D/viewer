#ifndef LINUX_CLIPBOARD_IMPL_H
#define LINUX_CLIPBOARD_IMPL_H

class ClipboardImpl
{
public:
    virtual void initialize(SDL_SysWMinfo const&) = 0;

    virtual bool hasClipboardText() = 0;

    virtual bool getSelectionText(bool primary, LLWString& text) = 0;
    virtual bool setSelectionText(bool primary, const LLWString& text) = 0;


    static ClipboardImpl* create( EDisplayServer );
};

#endif