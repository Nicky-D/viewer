/**
 * @file llfontvertexbuffer.cpp
 * @brief Buffer storage for font rendering.
 *
 * $LicenseInfo:firstyear=2024&license=viewerlgpl$
 * Second Life Viewer Source Code
 * Copyright (C) 2024, Linden Research, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation;
 * version 2.1 of the License only.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Linden Research, Inc., 945 Battery Street, San Francisco, CA  94111  USA
 * $/LicenseInfo$
 */

#include "linden_common.h"

#include "llfontvertexbuffer.h"

#include "llvertexbuffer.h"


LLFontVertexBuffer::LLFontVertexBuffer(bool track_changes)
: mTrackStringChanges(track_changes)
{
}

LLFontVertexBuffer::~LLFontVertexBuffer()
{
    reset();
}

void LLFontVertexBuffer::reset()
{
    mBufferList.clear();
}

S32 LLFontVertexBuffer::render(
    const LLFontGL* fontp,
    const LLWString& text,
    S32 begin_offset,
    F32 x, F32 y,
    const LLColor4& color,
    LLFontGL::HAlign halign, LLFontGL::VAlign valign,
    U8 style,
    LLFontGL::ShadowType shadow,
    S32 max_chars , S32 max_pixels,
    F32* right_x,
    bool use_ellipses,
    bool use_color )
{
    if (!LLFontGL::sDisplayFont) //do not display texts
    {
        return static_cast<S32>(text.length());
    }
    if (mBufferList.empty())
    {
        genBuffers(fontp, text, begin_offset, x, y, color, halign, valign,
            style, shadow, max_chars, max_pixels, right_x, use_ellipses, use_color);
    }
    else if (mLastX != x
             || mLastY != y
             || mLastFont != fontp
             || mLastColor != color // alphas change often
             || mLastHalign != halign
             || mLastValign != valign
             || mLastOffset != begin_offset
             || mLastMaxChars != max_chars
             || mLastMaxPixels != max_pixels
             || mLastStyle != style
             || mLastShadow != shadow // ex: buttons change shadow state
             || mLastScaleX != LLFontGL::sScaleX
             || mLastScaleY != LLFontGL::sScaleY
             || mLastOrigin != LLFontGL::sCurOrigin)
    {
        genBuffers(fontp, text, begin_offset, x, y, color, halign, valign,
            style, shadow, max_chars, max_pixels, right_x, use_ellipses, use_color);
    }
    else if (mTrackStringChanges && mLastStringHash != sStringHasher._Do_hash(text))
    {
        genBuffers(fontp, text, begin_offset, x, y, color, halign, valign,
            style, shadow, max_chars, max_pixels, right_x, use_ellipses, use_color);
    }
    else
    {
        renderBuffers();

        if (right_x)
        {
            *right_x = mLastRightX;
        }
    }
    return mChars;
}

void LLFontVertexBuffer::genBuffers(
    const LLFontGL* fontp,
    const LLWString& text,
    S32 begin_offset,
    F32 x, F32 y,
    const LLColor4& color,
    LLFontGL::HAlign halign, LLFontGL::VAlign valign,
    U8 style, LLFontGL::ShadowType shadow,
    S32 max_chars, S32 max_pixels,
    F32* right_x,
    bool use_ellipses,
    bool use_color)
{
    mBufferList.clear();

    gGL.beginList(&mBufferList);
    mChars = fontp->render(text, begin_offset, x, y, color, halign, valign,
        style, shadow, max_chars, max_pixels, right_x, use_ellipses, use_color);
    gGL.endList();

    mLastFont = fontp;
    mLastOffset = begin_offset;
    mLastMaxChars = max_chars;
    mLastMaxPixels = max_pixels;
    mLastStringHash = sStringHasher._Do_hash(text);
    mLastX = x;
    mLastY = y;
    mLastColor = color;
    mLastHalign = halign;
    mLastValign = valign;
    mLastStyle = style;
    mLastShadow = shadow;

    mLastScaleX = LLFontGL::sScaleX;
    mLastScaleY = LLFontGL::sScaleY;
    mLastOrigin = LLFontGL::sCurOrigin;

    if (right_x)
    {
        mLastRightX = *right_x;
    }
}

void LLFontVertexBuffer::renderBuffers()
{
    gGL.flush(); // deliberately empty pending verts
    gGL.getTexUnit(0)->enable(LLTexUnit::TT_TEXTURE);
    gGL.pushUIMatrix();
    for (LLVertexBufferData& buffer : mBufferList)
    {
        buffer.draw();
    }
    gGL.popUIMatrix();
}

