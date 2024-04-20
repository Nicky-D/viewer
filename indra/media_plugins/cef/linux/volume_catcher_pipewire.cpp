/** 
 * @file volume_catcher_pipewire.cpp
 * @brief A Linux-specific, PipeWire-specific hack to detect and volume-adjust new audio sources
 *
 * @cond
 * $LicenseInfo:firstyear=2010&license=viewerlgpl$
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
 * @endcond
 */

/*
  The high-level design is as follows:
  1) Connect to the PipeWire daemon
  2) Find all existing and new audio nodes
  3) Examine PID and parent PID's to see if it belongs to our process
  4) If so, tell PipeWire to adjust the volume of that node
  5) Keep a list of all audio nodes and adjust when we setVolume()
 */

#include "linden_common.h"

#include "volume_catcher_linux.h"

extern "C" {
#include <spa/pod/builder.h>
#include <spa/param/props.h>
}

SymbolGrabber pwSymbolGrabber;
#undef LL_SYMBOL_GRABBER
#define LL_SYMBOL_GRABBER pwSymbolGrabber

#include "volume_catcher_pipewire_syms.inc"

////////////////////////////////////////////////////

VolumeCatcherPipeWire::VolumeCatcherPipeWire()
{
	init();
}

VolumeCatcherPipeWire::~VolumeCatcherPipeWire()
{
	cleanup();
}

static void registryEventGlobal(
	void *data, uint32_t id, uint32_t permissions, const char *type,
	uint32_t version, const struct spa_dict *props
)
{
	static_cast<VolumeCatcherPipeWire*>(data)->handleRegistryEventGlobal(
		id, permissions, type, version, props
	);
}

static const struct pw_registry_events REGISTRY_EVENTS = {
	.version = PW_VERSION_REGISTRY_EVENTS,
    .global = registryEventGlobal,
};

bool VolumeCatcherPipeWire::loadsyms(std::string pw_dso_name)
{
	return pwSymbolGrabber.grabSymbols({ pw_dso_name });
}

void VolumeCatcherPipeWire::init()
{
	// debugPrint("init\n");
	
	mGotSyms = loadsyms("libpipewire-0.3.so.0");
	
	if (!mGotSyms)
		return;

	// debugPrint("got syms\n");

	llpw_init(NULL, NULL);

	mThreadLoop = llpw_thread_loop_new("SL Plugin Volume Adjuster", NULL);

	if (!mThreadLoop)
		return;

	// i dont think we need to lock this early
	// std::lock_guard pwLock(*this);

	mContext = llpw_context_new(
		llpw_thread_loop_get_loop(mThreadLoop), NULL, 0
	);

	if (!mContext)
		return;

	mCore = llpw_context_connect(mContext, NULL, 0);

	if (!mCore)
		return;

	mRegistry = pw_core_get_registry(mCore, PW_VERSION_REGISTRY, 0);

	// debugPrint("got registry\n");

	spa_zero(mRegistryListener);

	pw_registry_add_listener(
		mRegistry, &mRegistryListener, &REGISTRY_EVENTS, this
	);

	llpw_thread_loop_start(mThreadLoop);

	// debugPrint("started thread loop\n");
}

void VolumeCatcherPipeWire::cleanup()
{
	std::unique_lock childNodesLock(mChildNodesMutex);
	for (auto* childNode : mChildNodes) {
		childNode->destroy();
	}
	mChildNodes.clear();
	childNodesLock.unlock();

	std::unique_lock pwLock(*this);
	if (mRegistry)
		llpw_proxy_destroy((struct pw_proxy*)mRegistry);
	spa_zero(mRegistryListener);
	if (mCore)
		llpw_core_disconnect(mCore);
	if (mContext)
		llpw_context_destroy(mContext);
	pwLock.unlock();

	if (!mThreadLoop)
		return;

	llpw_thread_loop_stop(mThreadLoop);
	llpw_thread_loop_destroy(mThreadLoop);

	// debugPrint("cleanup done\n");
}

void VolumeCatcherPipeWire::lock() {
	if (!mThreadLoop)
		return;

	llpw_thread_loop_lock(mThreadLoop);
}

void VolumeCatcherPipeWire::unlock() {
	if (!mThreadLoop)
		return;

	llpw_thread_loop_unlock(mThreadLoop);
}

// #define INV_LERP(a, b, v) (v - a) / (b - a)

// #include <sys/time.h>

void VolumeCatcherPipeWire::ChildNode::updateVolume()
{
	if (!mActive)
		return;

	F32 volume = std::clamp(mImpl->mVolume, 0.0f, 1.0f);
	// F32 pan = std::clamp(mImpl->mPan, -1.0f, 1.0f);

	// debugClear();
	// struct timeval time;
	// gettimeofday(&time, NULL);
	// double t = (double)time.tv_sec + (double)(time.tv_usec / 1000) / 1000;
	// debugPrint("time is %f\n", t);
	// F32 pan = std::sin(t * 2.0d);
	// debugPrint("pan is %f\n", pan);

	// uint32_t channels = 2;
	// float volumes[channels];
	// volumes[1] = INV_LERP(-1.0f, 0.0f, pan) * volume; // left
	// volumes[0] = INV_LERP(1.0f, 0.0f, pan) * volume; // right

	uint32_t channels = 1;
	float volumes[channels];
	volumes[0] = volume;

	uint8_t buffer[512];

	spa_pod_builder builder;
	spa_pod_builder_init(&builder, buffer, sizeof(buffer));

	spa_pod_frame frame;
	spa_pod_builder_push_object(&builder, &frame, SPA_TYPE_OBJECT_Props, SPA_PARAM_Props);
	spa_pod_builder_prop(&builder, SPA_PROP_channelVolumes, 0);
	spa_pod_builder_array(&builder, sizeof(float), SPA_TYPE_Float, channels, volumes);
	spa_pod* pod = static_cast<spa_pod*>(spa_pod_builder_pop(&builder, &frame));

	std::lock_guard pwLock(*mImpl);

	pw_node_set_param(mProxy, SPA_PARAM_Props, 0, pod);
}

void VolumeCatcherPipeWire::ChildNode::destroy()
{
	if (!mActive)
		return;

	mActive = false;

	std::unique_lock childNodesLock(mImpl->mChildNodesMutex);
	mImpl->mChildNodes.erase(this);
	childNodesLock.unlock();
	
	spa_hook_remove(&mNodeListener);
	spa_hook_remove(&mProxyListener);

	std::lock_guard pwLock(*mImpl);

	llpw_proxy_destroy(mProxy);
}

static void nodeEventInfo(void* data, const struct pw_node_info* info)
{
	const char* processId = spa_dict_lookup(info->props, PW_KEY_APP_PROCESS_ID);

	if (processId == nullptr)
		return;
	
	pid_t pid = atoll(processId);

	if (!isPluginPid(pid))
		return;

	// const char* appName = spa_dict_lookup(info->props, PW_KEY_APP_NAME);
	// debugPrint("got app: %s\n", appName);
	
	auto* const childNode = static_cast<VolumeCatcherPipeWire::ChildNode*>(data);
	// debugPrint("init volume to: %f\n", childNode->mImpl->mVolume);

	childNode->updateVolume();

	std::lock_guard childNodesLock(childNode->mImpl->mChildNodesMutex);

	childNode->mImpl->mChildNodes.insert(childNode);
}

static const struct pw_node_events NODE_EVENTS = {
	.version = PW_VERSION_CLIENT_EVENTS,
	.info = nodeEventInfo,
};

static void proxyEventDestroy(void* data)
{
	auto* const childNode = static_cast<VolumeCatcherPipeWire::ChildNode*>(data);
	childNode->destroy();
}

static void proxyEventRemoved(void* data)
{
	auto* const childNode = static_cast<VolumeCatcherPipeWire::ChildNode*>(data);
	childNode->destroy();
}

static const struct pw_proxy_events PROXY_EVENTS = {
	.version = PW_VERSION_PROXY_EVENTS,
    .destroy = proxyEventDestroy,
	.removed = proxyEventRemoved,
};

void VolumeCatcherPipeWire::handleRegistryEventGlobal(
	uint32_t id, uint32_t permissions, const char *type, uint32_t version,
	const struct spa_dict *props
) {
	if (props == nullptr || strcmp(type, PW_TYPE_INTERFACE_Node) != 0)
		return;

	const char* mediaClass = spa_dict_lookup(props, PW_KEY_MEDIA_CLASS);
	
	if (mediaClass == nullptr || strcmp(mediaClass, "Stream/Output/Audio") != 0)
		return;
	
	pw_proxy* proxy = static_cast<pw_proxy*>(
		pw_registry_bind(mRegistry, id, type, PW_VERSION_CLIENT, sizeof(ChildNode))
	);

	auto* const childNode = static_cast<ChildNode*>(llpw_proxy_get_user_data(proxy));

	childNode->mActive = true;
	childNode->mProxy = proxy;
	childNode->mImpl = this;

	pw_node_add_listener(proxy, &childNode->mNodeListener, &NODE_EVENTS, childNode);
	llpw_proxy_add_listener(proxy, &childNode->mProxyListener, &PROXY_EVENTS, childNode);
}

void VolumeCatcherPipeWire::setVolume(F32 volume)
{
	// debugPrint("setting all volume to: %f\n", volume);

	mVolume = volume;

	std::unique_lock childNodeslock(mChildNodesMutex);
	std::unordered_set<ChildNode*> copyOfChildNodes(mChildNodes);
	childNodeslock.unlock();

	// debugPrint("for %d nodes\n", copyOfChildNodes.size());

	for (auto* childNode : copyOfChildNodes) {
		childNode->updateVolume();
	}
}

void VolumeCatcherPipeWire::setPan(F32 pan)
{
	// mPan = pan;
	// setVolume(mVolume);
}

void VolumeCatcherPipeWire::pump()
{
}