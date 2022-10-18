/** 
 * @file llimageworker.cpp
 * @brief Base class for images.
 *
 * $LicenseInfo:firstyear=2001&license=viewerlgpl$
 * Second Life Viewer Source Code
 * Copyright (C) 2010, Linden Research, Inc.
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

#include "llimageworker.h"
#include "llimagedxt.h"
#include "threadpool.h"

#include "llsys.h"

constexpr uint8_t MAX_THREADS_FALLBACK = 4;
/*--------------------------------------------------------------------------*/
class ImageRequest
{
public:
	ImageRequest(const LLPointer<LLImageFormatted>& image,
				 S32 discard, BOOL needs_aux,
				 const LLPointer<LLImageDecodeThread::Responder>& responder);
	virtual ~ImageRequest();

	/*virtual*/ bool processRequest();
	/*virtual*/ void finishRequest(bool completed);

private:
	// LLPointers stored in ImageRequest MUST be LLPointer instances rather
	// than references: we need to increment the refcount when storing these.
	// input
	LLPointer<LLImageFormatted> mFormattedImage;
	S32 mDiscardLevel;
	BOOL mNeedsAux;
	// output
	LLPointer<LLImageRaw> mDecodedImageRaw;
	LLPointer<LLImageRaw> mDecodedImageAux;
	BOOL mDecodedRaw;
	BOOL mDecodedAux;
	LLPointer<LLImageDecodeThread::Responder> mResponder;
};


//----------------------------------------------------------------------------

// MAIN THREAD
LLImageDecodeThread::LLImageDecodeThread(bool /*threaded*/)
{
#ifndef LL_LINUX
    mThreadPool.reset(new LL::ThreadPool("ImageDecode", 8));
    mThreadPool->start();
#endif
}

//virtual 
LLImageDecodeThread::~LLImageDecodeThread()
{}

#ifdef LL_LINUX
void LLImageDecodeThread::updateImplLinux()
{
    std::vector< std::shared_future<FutureResult> > vctNew;

    vctNew.reserve(mRequests.size() / 3);

    for( auto &f : mRequests )
    {
        auto ready = f.wait_for(std::chrono::microseconds(5));
        if (ready == std::future_status::ready)
        {
            FutureResult res = f.get();
            res.mRequest->finishRequest(res.mRequestResult);
            --mPending;
        }
        else
            vctNew.push_back(f);
    }

    std::swap(vctNew, mRequests);

    uint32_t numCPUS = gSysCPU.getNumCPUs();
    uint32_t threadsToCreate = MAX_THREADS_FALLBACK;

    if( numCPUS > 0 )
    {
        float fLoadAvg = gSysCPU.getLoadAvg();
        float fTarget = 0.8; // 80% load
        float fDiff = fTarget - fLoadAvg;
        if(fDiff <= 0 )
            threadsToCreate = 0;
        else
        {
            fDiff *= numCPUS;
            threadsToCreate = static_cast< uint32_t  >( fDiff );
        }
    }

    // Create at least 1
    if( mRequests.empty() && threadsToCreate == 0 )
        threadsToCreate = 1;

    if( mRequests.size() < threadsToCreate )
    {
        LLMutexLock _(&mMutex);
        auto newCreationList = mCreationList;
        mCreationList.clear();

        for(auto req: newCreationList)
        {
            if(mRequests.size() < threadsToCreate)
            {
                std::shared_future<FutureResult> f = std::async(std::launch::async,
                                                                [](ImageRequest *aReq) -> FutureResult {
                                                                    FutureResult res;
                                                                    res.mRequest = aReq;
                                                                    res.mRequestResult = aReq->processRequest();
                                                                    return res;
                                                                }, req);

                mRequests.emplace_back(f);
            }
            else
                mCreationList.emplace_back(req);
        }
    }
}
#endif

// MAIN THREAD
// virtual
S32 LLImageDecodeThread::update(F32 max_time_ms)
{
    LL_PROFILE_ZONE_SCOPED_CATEGORY_TEXTURE;
#ifdef LL_LINUX
    updateImplLinux();
#endif

    return getPending();
}

S32 LLImageDecodeThread::getPending()
{
#ifndef LL_LINUX
    return mThreadPool->getQueue().size();
#else
    return mPending;
#endif
}

LLImageDecodeThread::handle_t LLImageDecodeThread::decodeImage(
    const LLPointer<LLImageFormatted>& image, 
    S32 discard,
    BOOL needs_aux,
    const LLPointer<LLImageDecodeThread::Responder>& responder)
{
    LL_PROFILE_ZONE_SCOPED_CATEGORY_TEXTURE;

#ifndef LL_LINUX
    // Instantiate the ImageRequest right in the lambda, why not?
    mThreadPool->getQueue().post(
        [req = ImageRequest(image, discard, needs_aux, responder)]
        () mutable
        {
            auto done = req.processRequest();
            req.finishRequest(done);
        });
#else
    ++mPending;
    LLMutexLock _(&mMutex);
    mCreationList.emplace_back( new ImageRequest(image, discard, needs_aux, responder));
#endif

    // It's important to our consumer (LLTextureFetchWorker) that we return a
    // nonzero handle. It is NOT important that the nonzero handle be unique:
    // nothing is ever done with it except to compare it to zero, or zero it.
    return 17;
}

void LLImageDecodeThread::shutdown()
{
#ifndef LL_LINUX
    mThreadPool->close();
#endif
}

LLImageDecodeThread::Responder::~Responder()
{
}

//----------------------------------------------------------------------------

ImageRequest::ImageRequest(const LLPointer<LLImageFormatted>& image, 
							S32 discard, BOOL needs_aux,
							const LLPointer<LLImageDecodeThread::Responder>& responder)
	: mFormattedImage(image),
	  mDiscardLevel(discard),
	  mNeedsAux(needs_aux),
	  mDecodedRaw(FALSE),
	  mDecodedAux(FALSE),
	  mResponder(responder)
{
}

ImageRequest::~ImageRequest()
{
	mDecodedImageRaw = NULL;
	mDecodedImageAux = NULL;
	mFormattedImage = NULL;
}

//----------------------------------------------------------------------------


// Returns true when done, whether or not decode was successful.
bool ImageRequest::processRequest()
{
    LL_PROFILE_ZONE_SCOPED_CATEGORY_TEXTURE;
	const F32 decode_time_slice = 0.f; //disable time slicing
	bool done = true;
	if (!mDecodedRaw && mFormattedImage.notNull())
	{
		// Decode primary channels
		if (mDecodedImageRaw.isNull())
		{
			// parse formatted header
			if (!mFormattedImage->updateData())
			{
				return true; // done (failed)
			}
			if (0==(mFormattedImage->getWidth() * mFormattedImage->getHeight() * mFormattedImage->getComponents()))
			{
				return true; // done (failed)
			}
			if (mDiscardLevel >= 0)
			{
				mFormattedImage->setDiscardLevel(mDiscardLevel);
			}
			mDecodedImageRaw = new LLImageRaw(mFormattedImage->getWidth(),
											  mFormattedImage->getHeight(),
											  mFormattedImage->getComponents());
		}
		done = mFormattedImage->decode(mDecodedImageRaw, decode_time_slice);
		// some decoders are removing data when task is complete and there were errors
		mDecodedRaw = done && mDecodedImageRaw->getData();
	}
	if (done && mNeedsAux && !mDecodedAux && mFormattedImage.notNull())
	{
		// Decode aux channel
		if (!mDecodedImageAux)
		{
			mDecodedImageAux = new LLImageRaw(mFormattedImage->getWidth(),
											  mFormattedImage->getHeight(),
											  1);
		}
		done = mFormattedImage->decodeChannels(mDecodedImageAux, decode_time_slice, 4, 4);
		mDecodedAux = done && mDecodedImageAux->getData();
	}

	return done;
}

void ImageRequest::finishRequest(bool completed)
{
    LL_PROFILE_ZONE_SCOPED_CATEGORY_TEXTURE;
	if (mResponder.notNull())
	{
		bool success = completed && mDecodedRaw && (!mNeedsAux || mDecodedAux);
		mResponder->completed(success, mDecodedImageRaw, mDecodedImageAux);
	}
	// Will automatically be deleted
}
