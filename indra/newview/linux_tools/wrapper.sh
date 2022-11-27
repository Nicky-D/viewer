#!/bin/bash

## Here are some configuration options for Linux Client Testers.
## These options are for self-assisted troubleshooting during this beta
## testing phase; you should not usually need to touch them.

## - Avoids using any FMOD STUDIO audio driver.
#export LL_BAD_FMODSTUDIO_DRIVER=x
## - Avoids using any OpenAL audio driver.
#export LL_BAD_OPENAL_DRIVER=x

## - Avoids using the FMOD Studio or FMOD Ex PulseAudio audio driver.
#export LL_BAD_FMOD_PULSEAUDIO=x
## - Avoids using the FMOD Studio or FMOD Ex ALSA audio driver.
#export LL_BAD_FMOD_ALSA=x

## - Avoids the optional OpenGL extensions which have proven most problematic
##   on some hardware.  Disabling this option may cause BETTER PERFORMANCE but
##   may also cause CRASHES and hangs on some unstable combinations of drivers
##   and hardware.
## NOTE: This is now disabled by default.
#export LL_GL_BASICEXT=x

## - Avoids *all* optional OpenGL extensions.  This is the safest and least-
##   exciting option.  Enable this if you experience stability issues, and
##   report whether it helps in the Linux Client Testers forum.
#export LL_GL_NOEXT=x

## - For advanced troubleshooters, this lets you disable specific GL
##   extensions, each of which is represented by a letter a-o.  If you can
##   narrow down a stability problem on your system to just one or two
##   extensions then please post details of your hardware (and drivers) to
##   the Linux Client Testers forum along with the minimal
##   LL_GL_BLACKLIST which solves your problems.
#export LL_GL_BLACKLIST=abcdefghijklmno

## - Some ATI/Radeon users report random X server crashes when the mouse
##   cursor changes shape.  If you suspect that you are a victim of this
##   driver bug, try enabling this option and report whether it helps:
#export LL_ATI_MOUSE_CURSOR_BUG=x

## Everything below this line is just for advanced troubleshooters.
##-------------------------------------------------------------------

## - For advanced debugging cases, you can run the viewer under the
##   control of another program, such as strace, gdb, or valgrind.  If
##   you're building your own viewer, bear in mind that the executable
##   in the bin directory will be stripped: you should replace it with
##   an unstripped binary before you run.
#export LL_WRAPPER='gdb --args'
#export LL_WRAPPER='valgrind --smc-check=all --error-limit=no --log-file=secondlife.vg --leak-check=full --suppressions=/usr/lib/valgrind/glibc-2.5.supp --suppressions=secondlife-i686.supp'

## - Avoids an often-buggy X feature that doesn't really benefit us anyway.
export SDL_VIDEO_X11_DGAMOUSE=0

## - Automatically work around the ATI mouse cursor crash bug:
## (this workaround is disabled as most fglrx users do not see the bug)
#if lsmod | grep fglrx &>/dev/null ; then
#	export LL_ATI_MOUSE_CURSOR_BUG=x
#fi


## Nothing worth editing below this line.
##-------------------------------------------------------------------

SCRIPTSRC=`readlink -f "$0" || echo "$0"`
RUN_PATH=`dirname "${SCRIPTSRC}" || echo .`
echo "Running from ${RUN_PATH}"
cd "${RUN_PATH}"

# Re-register the secondlife:// protocol handler every launch, for now.
./etc/register_secondlifeprotocol.sh

# Re-register the application with the desktop system every launch, for now.
./etc/refresh_desktop_app_entry.sh

## Before we mess with LD_LIBRARY_PATH, save the old one to restore for
##  subprocesses that care.
export SAVED_LD_LIBRARY_PATH="${LD_LIBRARY_PATH}"

export LD_LIBRARY_PATH="$PWD/lib:$PWD/lib32:${LD_LIBRARY_PATH}"

if [ -f  lib/libjemalloc.so ]
then
	echo "Using jemalloc"
	export LD_PRELOAD="lib/libjemalloc.so"
fi

# Copy "$@" to ARGS array specifically to delete the --skip-gridargs switch.
# The gridargs.dat file is no more, but we still want to avoid breaking
# scripts that invoke this one with --skip-gridargs.
ARGS=()
for ARG in "$@"; do
    if [ "--skip-gridargs" != "$ARG" ]; then
        ARGS[${#ARGS[*]}]="$ARG"
    fi
done

# Run the program.
# Don't quote $LL_WRAPPER because, if empty, it should simply vanish from the
# command line. But DO quote "${ARGS[@]}": preserve separate args as
# individually quoted.
$LL_WRAPPER bin/do-not-directly-run-secondlife-bin "${ARGS[@]}"
LL_RUN_ERR=$?

# Handle any resulting errors
if [ $LL_RUN_ERR -ne 0 ]; then
	# generic error running the binary
	echo '*** Bad shutdown ($LL_RUN_ERR). ***'
fi
