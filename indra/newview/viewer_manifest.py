#!/usr/bin/env python3
"""\
@file viewer_manifest.py
@author Ryan Williams
@brief Description of all installer viewer files, and methods for packaging
       them into installers for all supported platforms.

$LicenseInfo:firstyear=2006&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2006-2014, Linden Research, Inc.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation;
version 2.1 of the License only.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Linden Research, Inc., 945 Battery Street, San Francisco, CA  94111  USA
$/LicenseInfo$
"""
import errno
import glob
import itertools
import json
import os
import os.path
import plistlib
import random
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

viewer_dir = os.path.dirname(__file__)
# Add indra/lib/python to our path so we don't have to muck with PYTHONPATH.
# Put it FIRST because some of our build hosts have an ancient install of
# indra.util.llmanifest under their system Python!
sys.path.insert(0, os.path.join(viewer_dir, os.pardir, "lib", "python"))
from indra.util.llmanifest import LLManifest, main, path_ancestors, CHANNEL_VENDOR_BASE, RELEASE_CHANNEL, ManifestError, MissingError

try:
    import llsd
    LLBASE_IMPORTED=True
except:
    LLBASE_IMPORTED=False
    
class ViewerManifest(LLManifest):
    def is_packaging_viewer(self):
        # Some commands, files will only be included
        # if we are packaging the viewer on windows.
        # This manifest is also used to copy
        # files during the build (see copy_w_viewer_manifest
        # and copy_l_viewer_manifest targets)
        return 'package' in self.args['actions']
    
    def construct(self):
        super(ViewerManifest, self).construct()
        self.path(src="../../scripts/messages/message_template.msg", dst="app_settings/message_template.msg")
        self.path(src="../../etc/message.xml", dst="app_settings/message.xml")

        if self.is_packaging_viewer():
            with self.prefix(src_dst="app_settings"):
                self.exclude("logcontrol.xml")
                self.exclude("logcontrol-dev.xml")
                self.path("*.ini")
                self.path("*.xml")

                # include the entire shaders directory recursively
                self.path("shaders")
                # include the extracted list of contributors
                contributions_path = os.path.join(self.args['source'], "..", "..", "doc", "contributions.txt")
                contributor_names = self.extract_names(contributions_path)
                self.put_in_file(contributor_names.encode(), "contributors.txt", src=contributions_path)

                # ... and the default camera position settings
                self.path("camera")

                # ... and the entire windlight directory
                self.path("windlight")

                # ... and the entire image filters directory
                self.path("filters")
            
                # ... and the included spell checking dictionaries
                pkgdir = os.path.join(self.args['build'], os.pardir, 'packages')
                with self.prefix(src=pkgdir):
                    self.path_optional("dictionaries")

                if "package_dir" in self.args:
                    with self.prefix(src=self.args['package_dir']):
                        self.path_optional("dictionaries")
                    
                # include the extracted packages information (see BuildPackagesInfo.cmake)
                self.path(src=os.path.join(self.args['build'],"packages-info.txt"), dst="packages-info.txt")
                # CHOP-955: If we have "sourceid" or "viewer_channel" in the
                # build process environment, generate it into
                # settings_install.xml.
                settings_template = dict(
                    sourceid=dict(Comment='Identify referring agency to Linden web servers',
                                  Persist=1,
                                  Type='String',
                                  Value=''),
                    CmdLineGridChoice=dict(Comment='Default grid',
                                  Persist=0,
                                  Type='String',
                                  Value=''),
                    CmdLineChannel=dict(Comment='Command line specified channel name',
                                        Persist=0,
                                        Type='String',
                                        Value=''))
                settings_install = {}
                sourceid = self.args.get('sourceid')
                if sourceid:
                    settings_install['sourceid'] = settings_template['sourceid'].copy()
                    settings_install['sourceid']['Value'] = sourceid
                    print("Set sourceid in settings_install.xml to '%s'" % sourceid)

                if self.args.get('channel_suffix'):
                    settings_install['CmdLineChannel'] = settings_template['CmdLineChannel'].copy()
                    settings_install['CmdLineChannel']['Value'] = self.channel_with_pkg_suffix()
                    print("Set CmdLineChannel in settings_install.xml to '%s'" % self.channel_with_pkg_suffix())

                if self.args.get('grid'):
                    settings_install['CmdLineGridChoice'] = settings_template['CmdLineGridChoice'].copy()
                    settings_install['CmdLineGridChoice']['Value'] = self.grid()
                    print("Set CmdLineGridChoice in settings_install.xml to '%s'" % self.grid())

                # put_in_file(src=) need not be an actual pathname; it
                # only needs to be non-empty
                if LLBASE_IMPORTED:
                    self.put_in_file(llsd.format_pretty_xml(settings_install),
                                     "settings_install.xml",
                                     src="environment")


            with self.prefix(src_dst="character"):
                self.path("*.llm")
                self.path("*.xml")
                self.path("*.tga")

            # Include our fonts
            with self.prefix(src_dst="fonts"):
                self.path("*.ttf")
                self.path("*.txt")

            # skins
            with self.prefix(src_dst="skins"):
                    # include the entire textures directory recursively
                    with self.prefix(src_dst="*/textures"):
                            self.path("*/*.jpg")
                            self.path("*/*.png")
                            self.path("*.tga")
                            self.path("*.j2c")
                            self.path("*.png")
                            self.path("textures.xml")
                    self.path("*/xui/*/*.xml")
                    self.path("*/xui/*/widgets/*.xml")
                    self.path("*/*.xml")

                    # Update: 2017-11-01 CP Now we store app code in the html folder
                    #         Initially the HTML/JS code to render equirectangular
                    #         images for the 360 capture feature but more to follow.
                    with self.prefix(src="*/html", dst="*/html"):
                        self.path("*/*/*/*.js")
                        self.path("*/*/*.html")

            #build_data.json.  Standard with exception handling is fine.  If we can't open a new file for writing, we have worse problems
            #platform is computed above with other arg parsing
            build_data_dict = {"Type":"viewer","Version":'.'.join(self.args['version']),
                            "Channel Base": CHANNEL_VENDOR_BASE,
                            "Channel":self.channel_with_pkg_suffix(),
                            "Platform":self.build_data_json_platform,
                            "Address Size":self.address_size,
                            "Update Service":"https://update.secondlife.com/update",
                            }
            # Only store this if it's both present and non-empty
            bugsplat_db = self.args.get('bugsplat')
            if bugsplat_db:
                build_data_dict["BugSplat DB"] = bugsplat_db
            build_data_dict = self.finish_build_data_dict(build_data_dict)
            with open(os.path.join(os.pardir,'build_data.json'), 'w') as build_data_handle:
                json.dump(build_data_dict,build_data_handle)

            #we likely no longer need the test, since we will throw an exception above, but belt and suspenders and we get the
            #return code for free.
            if not self.path2basename(os.pardir, "build_data.json"):
                print("No build_data.json file")

    def finish_build_data_dict(self, build_data_dict):
        return build_data_dict

    def grid(self):
        return self.args['grid']

    def channel(self):
        return self.args['channel']

    def channel_with_pkg_suffix(self):
        fullchannel=self.channel()
        channel_suffix = self.args.get('channel_suffix')
        if channel_suffix:
            fullchannel+=' '+channel_suffix
        return fullchannel

    def channel_variant(self):
        global CHANNEL_VENDOR_BASE
        return self.channel().replace(CHANNEL_VENDOR_BASE, "").strip()

    def channel_type(self): # returns 'release', 'beta', 'project', or 'test'
        channel_qualifier=self.channel_variant().lower()
        if channel_qualifier.startswith('release'):
            channel_type='release'
        elif channel_qualifier.startswith('beta'):
            channel_type='beta'
        elif channel_qualifier.startswith('project'):
            channel_type='project'
        else:
            channel_type='test'
        return channel_type

    def channel_variant_app_suffix(self):
        # get any part of the channel name after the CHANNEL_VENDOR_BASE
        suffix=self.channel_variant()
        # by ancient convention, we don't use Release in the app name
        if self.channel_type() == 'release':
            suffix=suffix.replace('Release', '').strip()
        # for the base release viewer, suffix will now be null - for any other, append what remains
        if suffix:
            suffix = "_".join([''] + suffix.split())
        # the additional_packages mechanism adds more to the installer name (but not to the app name itself)
        # ''.split() produces empty list, so suffix only changes if
        # channel_suffix is non-empty
        suffix = "_".join([suffix] + self.args.get('channel_suffix', '').split())
        return suffix

    def installer_base_name(self):
        global CHANNEL_VENDOR_BASE
        # a standard map of strings for replacing in the templates
        substitution_strings = {
            'channel_vendor_base' : '_'.join(CHANNEL_VENDOR_BASE.split()),
            'channel_variant_underscores':self.channel_variant_app_suffix(),
            'version_underscores' : '_'.join(self.args['version']),
            'arch':self.args['arch']
            }
        return "%(channel_vendor_base)s%(channel_variant_underscores)s_%(version_underscores)s_%(arch)s" % substitution_strings

    def app_name(self):
        global CHANNEL_VENDOR_BASE
        channel_type=self.channel_type()
        if channel_type == 'release':
            app_suffix='Viewer'
        else:
            app_suffix=self.channel_variant()
        return CHANNEL_VENDOR_BASE + ' ' + app_suffix

    def exec_name(self):
        return "SecondLifeViewer"

    def app_name_oneword(self):
        return ''.join(self.app_name().split())
    
    def icon_path(self):
        return "icons/" + self.channel_type()

    def extract_names(self,src):
        """Extract contributor names from source file, returns string"""
        try:
            with open(src, 'r') as contrib_file: 
                lines = contrib_file.readlines()
        except IOError:
            print("Failed to open '%s'" % src)
            raise

        # All lines up to and including the first blank line are the file header; skip them
        lines.reverse() # so that pop will pull from first to last line
        while not re.match("\s*$", lines.pop()) :
            pass # do nothing

        # A line that starts with a non-whitespace character is a name; all others describe contributions, so collect the names
        names = []
        for line in lines :
            if re.match("\S", line) :
                names.append(line.rstrip())
        # It's not fair to always put the same people at the head of the list
        random.shuffle(names)
        return ', '.join(names)

    def relsymlinkf(self, src, dst=None, catch=True):
        """
        relsymlinkf() is just like symlinkf(), but instead of requiring the
        caller to pass 'src' as a relative pathname, this method expects 'src'
        to be absolute, and creates a symlink whose target is the relative
        path from 'src' to dirname(dst).
        """
        dstdir, dst = self._symlinkf_prep_dst(src, dst)

        # Determine the relative path starting from the directory containing
        # dst to the intended src.
        src = self.relpath(src, dstdir)

        self._symlinkf(src, dst, catch)
        return dst

    def symlinkf(self, src, dst=None, catch=True):
        """
        Like ln -sf, but uses os.symlink() instead of running ln. This creates
        a symlink at 'dst' that points to 'src' -- see:
        https://docs.python.org/3/library/os.html#os.symlink

        If you omit 'dst', this creates a symlink with basename(src) at
        get_dst_prefix() -- in other words: put a symlink to this pathname
        here at the current dst prefix.

        'src' must specifically be a *relative* symlink. It makes no sense to
        create an absolute symlink pointing to some path on the build machine!

        Also:
        - We prepend 'dst' with the current get_dst_prefix(), so it has similar
          meaning to associated self.path() calls.
        - We ensure that the containing directory os.path.dirname(dst) exists
          before attempting the symlink.

        If you pass catch=False, exceptions will be propagated instead of
        caught.
        """
        dstdir, dst = self._symlinkf_prep_dst(src, dst)
        self._symlinkf(src, dst, catch)
        return dst

    def _symlinkf_prep_dst(self, src, dst):
        # helper for relsymlinkf() and symlinkf()
        if dst is None:
            dst = os.path.basename(src)
        dst = os.path.join(self.get_dst_prefix(), dst)
        # Seems silly to prepend get_dst_prefix() to dst only to call
        # os.path.dirname() on it again, but this works even when the passed
        # 'dst' is itself a pathname.
        dstdir = os.path.dirname(dst)
        self.cmakedirs(dstdir)
        return (dstdir, dst)

    def _symlinkf(self, src, dst, catch):
        # helper for relsymlinkf() and symlinkf()
        # the passed src must be relative
        if os.path.isabs(src):
            raise ManifestError("Do not symlinkf(absolute %r, asis=True)" % src)

        # The outer catch is the one that reports failure even after attempted
        # recovery.
        try:
            # At the inner layer, recovery may be possible.
            try:
                os.symlink(src, dst)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                # We could just blithely attempt to remove and recreate the target
                # file, but that strategy doesn't work so well if we don't have
                # permissions to remove it. Check to see if it's already the
                # symlink we want, which is the usual reason for EEXIST.
                elif os.path.islink(dst):
                    if os.readlink(dst) == src:
                        # the requested link already exists
                        pass
                    else:
                        # dst is the wrong symlink; attempt to remove and recreate it
                        os.remove(dst)
                        os.symlink(src, dst)
                elif os.path.isdir(dst):
                    print("Requested symlink (%s) exists but is a directory; replacing" % dst)
                    shutil.rmtree(dst)
                    os.symlink(src, dst)
                elif os.path.exists(dst):
                    print("Requested symlink (%s) exists but is a file; replacing" % dst)
                    os.remove(dst)
                    os.symlink(src, dst)
                else:
                    # out of ideas
                    raise
        except Exception as err:
            # report
            print("Can't symlink %r -> %r: %s: %s" % \
                  (dst, src, err.__class__.__name__, err))
            # if caller asked us not to catch, re-raise this exception
            if not catch:
                raise

    def relpath(self, path, base=None, symlink=False):
        """
        Return the relative path from 'base' to the passed 'path'. If base is
        omitted, self.get_dst_prefix() is assumed. In other words: make a
        same-name symlink to this path right here in the current dest prefix.

        Normally we resolve symlinks. To retain symlinks, pass symlink=True.
        """
        if base is None:
            base = self.get_dst_prefix()

        # Since we use os.path.relpath() for this, which is purely textual, we
        # must ensure that both pathnames are absolute.
        if symlink:
            # symlink=True means: we know path is (or indirects through) a
            # symlink, don't resolve, we want to use the symlink.
            abspath = os.path.abspath
        else:
            # symlink=False means to resolve any symlinks we may find
            abspath = os.path.realpath

        return os.path.relpath(abspath(path), abspath(base))


class WindowsManifest(ViewerManifest):
    # We want the platform, per se, for every Windows build to be 'win'. The
    # VMP will concatenate that with the address_size.
    build_data_json_platform = 'win'

    def final_exe(self):
        return self.exec_name()+".exe"

    def finish_build_data_dict(self, build_data_dict):
        build_data_dict['Executable'] = self.final_exe()
        build_data_dict['AppName']    = self.app_name()
        return build_data_dict

    def test_msvcrt_and_copy_action(self, src, dst):
        # This is used to test a dll manifest.
        # It is used as a temporary override during the construct method
        from test_win32_manifest import test_assembly_binding
        # TODO: This is redundant with LLManifest.copy_action(). Why aren't we
        # calling copy_action() in conjunction with test_assembly_binding()?
        if src and (os.path.exists(src) or os.path.islink(src)):
            # ensure that destination path exists
            self.cmakedirs(os.path.dirname(dst))
            self.created_paths.append(dst)
            if not os.path.isdir(src):
                if(self.args['buildtype'].lower() == 'debug'):
                    test_assembly_binding(src, "Microsoft.VC80.DebugCRT", "8.0.50727.4053")
                else:
                    test_assembly_binding(src, "Microsoft.VC80.CRT", "8.0.50727.4053")
                self.ccopy(src,dst)
            else:
                raise Exception("Directories are not supported by test_CRT_and_copy_action()")
        else:
            print("Doesn't exist:", src)

    def test_for_no_msvcrt_manifest_and_copy_action(self, src, dst):
        # This is used to test that no manifest for the msvcrt exists.
        # It is used as a temporary override during the construct method
        from test_win32_manifest import test_assembly_binding
        from test_win32_manifest import NoManifestException, NoMatchingAssemblyException
        # TODO: This is redundant with LLManifest.copy_action(). Why aren't we
        # calling copy_action() in conjunction with test_assembly_binding()?
        if src and (os.path.exists(src) or os.path.islink(src)):
            # ensure that destination path exists
            self.cmakedirs(os.path.dirname(dst))
            self.created_paths.append(dst)
            if not os.path.isdir(src):
                try:
                    if(self.args['buildtype'].lower() == 'debug'):
                        test_assembly_binding(src, "Microsoft.VC80.DebugCRT", "")
                    else:
                        test_assembly_binding(src, "Microsoft.VC80.CRT", "")
                    raise Exception("Unknown condition")
                except NoManifestException as err:
                    pass
                except NoMatchingAssemblyException as err:
                    pass

                self.ccopy(src,dst)
            else:
                raise Exception("Directories are not supported by test_CRT_and_copy_action()")
        else:
            print("Doesn't exist:", src)
        
    def construct(self):
        super(WindowsManifest, self).construct()

        pkgdir = os.path.join(self.args['build'], os.pardir, 'packages')
        relpkgdir = os.path.join(pkgdir, "lib", "release")
        debpkgdir = os.path.join(pkgdir, "lib", "debug")

        if self.is_packaging_viewer():
            # Find secondlife-bin.exe in the 'configuration' dir, then rename it to the result of final_exe.
            self.path(src='%s/secondlife-bin.exe' % self.args['configuration'], dst=self.final_exe())

            with self.prefix(src=os.path.join(pkgdir, "VMP")):
                # include the compiled launcher scripts so that it gets included in the file_list
                self.path('SLVersionChecker.exe')

            with self.prefix(dst="vmp_icons"):
                with self.prefix(src=self.icon_path()):
                    self.path("secondlife.ico")
                #VMP  Tkinter icons
                with self.prefix(src="vmp_icons"):
                    self.path("*.png")
                    self.path("*.gif")

        # Plugin host application
        self.path2basename(os.path.join(os.pardir,
                                        'llplugin', 'slplugin', self.args['configuration']),
                           "slplugin.exe")
        
        # Get shared libs from the shared libs staging directory
        with self.prefix(src=os.path.join(self.args['build'], os.pardir,
                                          'sharedlibs', self.args['buildtype'])):
            # Get fmodstudio dll if needed
            if self.args['fmodstudio'] == 'ON':
                if(self.args['buildtype'].lower() == 'debug'):
                    self.path("fmodL.dll")
                else:
                    self.path("fmod.dll")

            if self.args['openal'] == 'ON':
                # Get openal dll
                self.path("OpenAL32.dll")
                self.path("alut.dll")

            # For textures
            self.path("openjp2.dll")

            # Uriparser
            self.path("uriparser.dll")

            # These need to be installed as a SxS assembly, currently a 'private' assembly.
            # See http://msdn.microsoft.com/en-us/library/ms235291(VS.80).aspx
            self.path("msvcp140.dll")
            self.path("vcruntime140.dll")
            self.path_optional("vcruntime140_1.dll")

            # SLVoice executable
            with self.prefix(src=os.path.join(pkgdir, 'bin', 'release')):
                self.path("SLVoice.exe")

            # Vivox libraries
            if (self.address_size == 64):
                self.path("vivoxsdk_x64.dll")
                self.path("ortp_x64.dll")
            else:
                self.path("vivoxsdk.dll")
                self.path("ortp.dll")
            
            # OpenSSL
            if (self.address_size == 64):
                self.path("libcrypto-1_1-x64.dll")
                self.path("libssl-1_1-x64.dll")
            else:
                self.path("libcrypto-1_1.dll")
                self.path("libssl-1_1.dll")

            # HTTP/2
            self.path("nghttp2.dll")

            # Hunspell
            self.path("libhunspell.dll")

            # BugSplat
            if self.args.get('bugsplat'):
                if(self.address_size == 64):
                    self.path("BsSndRpt64.exe")
                    self.path("BugSplat64.dll")
                    self.path("BugSplatRc64.dll")
                else:
                    self.path("BsSndRpt.exe")
                    self.path("BugSplat.dll")
                    self.path("BugSplatRc.dll")

        self.path(src="licenses-win32.txt", dst="licenses.txt")
        self.path("featuretable.txt")
        self.path("cube.dae")

        with self.prefix(src=pkgdir):
            self.path("ca-bundle.crt")

        # Media plugins - CEF
        with self.prefix(dst="llplugin"):
            with self.prefix(src=os.path.join(self.args['build'], os.pardir, 'media_plugins')):
                with self.prefix(src=os.path.join('cef', self.args['configuration'])):
                    self.path("media_plugin_cef.dll")

                # Media plugins - LibVLC
                with self.prefix(src=os.path.join('libvlc', self.args['configuration'])):
                    self.path("media_plugin_libvlc.dll")

                # Media plugins - Example (useful for debugging - not shipped with release viewer)
                if self.channel_type() != 'release':
                    with self.prefix(src=os.path.join('example', self.args['configuration'])):
                        self.path("media_plugin_example.dll")

            # CEF runtime files - debug
            # CEF runtime files - not debug (release, relwithdebinfo etc.)
            config = 'debug' if self.args['configuration'].lower() == 'debug' else 'release'
            with self.prefix(src=os.path.join(pkgdir, 'bin', config)):
                self.path("chrome_elf.dll")
                self.path("d3dcompiler_47.dll")
                self.path("libcef.dll")
                self.path("libEGL.dll")
                self.path("libGLESv2.dll")
                self.path("dullahan_host.exe")
                self.path("snapshot_blob.bin")
                self.path("v8_context_snapshot.bin")

            # MSVC DLLs needed for CEF and have to be in same directory as plugin
            with self.prefix(src=os.path.join(self.args['build'], os.pardir,
                                              'sharedlibs', self.args['buildtype'])):
                self.path("msvcp140.dll")
                self.path("vcruntime140.dll")
                self.path_optional("vcruntime140_1.dll")

            # CEF files common to all configurations
            with self.prefix(src=os.path.join(pkgdir, 'resources')):
                self.path("chrome_100_percent.pak")
                self.path("chrome_200_percent.pak")
                self.path("resources.pak")
                self.path("icudtl.dat")

            with self.prefix(src=os.path.join(pkgdir, 'resources', 'locales'), dst='locales'):
                self.path("am.pak")
                self.path("ar.pak")
                self.path("bg.pak")
                self.path("bn.pak")
                self.path("ca.pak")
                self.path("cs.pak")
                self.path("da.pak")
                self.path("de.pak")
                self.path("el.pak")
                self.path("en-GB.pak")
                self.path("en-US.pak")
                self.path("es-419.pak")
                self.path("es.pak")
                self.path("et.pak")
                self.path("fa.pak")
                self.path("fi.pak")
                self.path("fil.pak")
                self.path("fr.pak")
                self.path("gu.pak")
                self.path("he.pak")
                self.path("hi.pak")
                self.path("hr.pak")
                self.path("hu.pak")
                self.path("id.pak")
                self.path("it.pak")
                self.path("ja.pak")
                self.path("kn.pak")
                self.path("ko.pak")
                self.path("lt.pak")
                self.path("lv.pak")
                self.path("ml.pak")
                self.path("mr.pak")
                self.path("ms.pak")
                self.path("nb.pak")
                self.path("nl.pak")
                self.path("pl.pak")
                self.path("pt-BR.pak")
                self.path("pt-PT.pak")
                self.path("ro.pak")
                self.path("ru.pak")
                self.path("sk.pak")
                self.path("sl.pak")
                self.path("sr.pak")
                self.path("sv.pak")
                self.path("sw.pak")
                self.path("ta.pak")
                self.path("te.pak")
                self.path("th.pak")
                self.path("tr.pak")
                self.path("uk.pak")
                self.path("vi.pak")
                self.path("zh-CN.pak")
                self.path("zh-TW.pak")

            with self.prefix(src=os.path.join(pkgdir, 'bin', 'release')):
                self.path("libvlc.dll")
                self.path("libvlccore.dll")
                self.path("plugins/")

        if not self.is_packaging_viewer():
            self.package_file = "copied_deps"    

    def nsi_file_commands(self, install=True):
        def wpath(path):
            if path.endswith('/') or path.endswith(os.path.sep):
                path = path[:-1]
            path = path.replace('/', '\\')
            return path

        result = ""
        dest_files = [pair[1] for pair in self.file_list if pair[0] and os.path.isfile(pair[1])]
        # sort deepest hierarchy first
        dest_files.sort(key=lambda f: (f.count(os.path.sep), f), reverse=True)
        out_path = None
        for pkg_file in dest_files:
            rel_file = os.path.normpath(pkg_file.replace(self.get_dst_prefix()+os.path.sep,''))
            installed_dir = wpath(os.path.join('$INSTDIR', os.path.dirname(rel_file)))
            pkg_file = wpath(os.path.normpath(pkg_file))
            if installed_dir != out_path:
                if install:
                    out_path = installed_dir
                    result += 'SetOutPath ' + out_path + '\n'
            if install:
                result += 'File ' + pkg_file + '\n'
            else:
                result += 'Delete ' + wpath(os.path.join('$INSTDIR', rel_file)) + '\n'

        # at the end of a delete, just rmdir all the directories
        if not install:
            deleted_file_dirs = [os.path.dirname(pair[1].replace(self.get_dst_prefix()+os.path.sep,'')) for pair in self.file_list]
            # find all ancestors so that we don't skip any dirs that happened to have no non-dir children
            deleted_dirs = []
            for d in deleted_file_dirs:
                deleted_dirs.extend(path_ancestors(d))
            # sort deepest hierarchy first
            deleted_dirs.sort(key=lambda f: (f.count(os.path.sep), f), reverse=True)
            prev = None
            for d in deleted_dirs:
                if d != prev:   # skip duplicates
                    result += 'RMDir ' + wpath(os.path.join('$INSTDIR', os.path.normpath(d))) + '\n'
                prev = d

        return result

    def package_finish(self):
        # a standard map of strings for replacing in the templates
        substitution_strings = {
            'version' : '.'.join(self.args['version']),
            'version_short' : '.'.join(self.args['version'][:-1]),
            'version_dashes' : '-'.join(self.args['version']),
            'version_registry' : '%s(%s)' %
            ('.'.join(self.args['version']), self.address_size),
            'final_exe' : self.final_exe(),
            'flags':'',
            'app_name':self.app_name(),
            'app_name_oneword':self.app_name_oneword()
            }

        installer_file = self.installer_base_name() + '_Setup.exe'
        substitution_strings['installer_file'] = installer_file
        
        version_vars = """
        !define INSTEXE "SLVersionChecker.exe"
        !define VERSION "%(version_short)s"
        !define VERSION_LONG "%(version)s"
        !define VERSION_DASHES "%(version_dashes)s"
        !define VERSION_REGISTRY "%(version_registry)s"
        !define VIEWER_EXE "%(final_exe)s"
        """ % substitution_strings
        
        if self.channel_type() == 'release':
            substitution_strings['caption'] = CHANNEL_VENDOR_BASE
        else:
            substitution_strings['caption'] = self.app_name() + ' ${VERSION}'

        inst_vars_template = """
            OutFile "%(installer_file)s"
            !define INSTNAME   "%(app_name_oneword)s"
            !define SHORTCUT   "%(app_name)s"
            !define URLNAME   "secondlife"
            Caption "%(caption)s"
            """

        if(self.address_size == 64):
            engage_registry="SetRegView 64"
            program_files="!define MULTIUSER_USE_PROGRAMFILES64"
        else:
            engage_registry="SetRegView 32"
            program_files=""

        tempfile = "secondlife_setup_tmp.nsi"
        # the following replaces strings in the nsi template
        # it also does python-style % substitution
        self.replace_in("installers/windows/installer_template.nsi", tempfile, {
                "%%VERSION%%":version_vars,
                "%%SOURCE%%":self.get_src_prefix(),
                "%%INST_VARS%%":inst_vars_template % substitution_strings,
                "%%INSTALL_FILES%%":self.nsi_file_commands(True),
                "%%PROGRAMFILES%%":program_files,
                "%%ENGAGEREGISTRY%%":engage_registry,
                "%%DELETE_FILES%%":self.nsi_file_commands(False)})

        # If we're on a build machine, sign the code using our Authenticode certificate. JC
        # note that the enclosing setup exe is signed later, after the makensis makes it.
        # Unlike the viewer binary, the VMP filenames are invariant with respect to version, os, etc.
        for exe in (
            self.final_exe(),
            "SLVersionChecker.exe",
            "llplugin/dullahan_host.exe",
            ):
            self.sign(exe)
            
        # Check two paths, one for Program Files, and one for Program Files (x86).
        # Yay 64bit windows.
        nsis_path = "makensis.exe"
        for program_files in '${programfiles}', '${programfiles(x86)}':
            for nesis_path in 'NSIS', 'NSIS\\Unicode':
                possible_path = os.path.expandvars(f"{program_files}\\{nesis_path}\\makensis.exe")
                if os.path.exists(possible_path):
                    nsis_path = possible_path
                    break

        self.run_command([possible_path, '/V2', self.dst_path_of(tempfile)])

        self.sign(installer_file)
        self.created_path(self.dst_path_of(installer_file))
        self.package_file = installer_file

    def sign(self, exe):
        sign_py = os.environ.get('SIGN', r'C:\buildscripts\code-signing\sign.py')
        python  = os.environ.get('PYTHON', sys.executable)
        if os.path.exists(sign_py):
            dst_path = self.dst_path_of(exe)
            print("about to run signing of: ", dst_path)
            self.run_command([python, sign_py, dst_path])
        else:
            print("Skipping code signing of %s %s: %s not found" % (self.dst_path_of(exe), exe, sign_py))

    def escape_slashes(self, path):
        return path.replace('\\', '\\\\\\\\')

class Windows_i686_Manifest(WindowsManifest):
    # Although we aren't literally passed ADDRESS_SIZE, we can infer it from
    # the passed 'arch', which is used to select the specific subclass.
    address_size = 32

class Windows_x86_64_Manifest(WindowsManifest):
    address_size = 64


class DarwinManifest(ViewerManifest):
    build_data_json_platform = 'mac'

    def finish_build_data_dict(self, build_data_dict):
        build_data_dict.update({'Bundle Id':self.args['bundleid']})
        return build_data_dict

    def is_packaging_viewer(self):
        # darwin requires full app bundle packaging even for debugging.
        return True

    def is_rearranging(self):
        # That said, some stuff should still only be performed once.
        # Are either of these actions in 'actions'? Is the set intersection
        # non-empty?
        return bool(set(["package", "unpacked"]).intersection(self.args['actions']))

    def construct(self):
        # copy over the build result (this is a no-op if run within the xcode script)
        self.path(os.path.join(self.args['configuration'], self.channel()+".app"), dst="")

        pkgdir = os.path.join(self.args['build'], os.pardir, 'packages')
        relpkgdir = os.path.join(pkgdir, "lib", "release")
        debpkgdir = os.path.join(pkgdir, "lib", "debug")

        with self.prefix(src="", dst="Contents"):  # everything goes in Contents
            bugsplat_db = self.args.get('bugsplat')
            if bugsplat_db:
                # Inject BugsplatServerURL into Info.plist if provided.
                Info_plist = self.dst_path_of("Info.plist")
                with open(Info_plist, 'rb') as f:
                    Info = plistlib.load(f)
                    # https://www.bugsplat.com/docs/platforms/os-x#configuration
                    Info["BugsplatServerURL"] = \
                        "https://{}.bugsplat.com/".format(bugsplat_db)
                    self.put_in_file(
                        plistlib.dumps(Info),
                        os.path.basename(Info_plist),
                        "Info.plist")

            # CEF framework goes inside Contents/Frameworks.
            # Remember where we parked this car.
            with self.prefix(src="", dst="Frameworks"):
                CEF_framework = "Chromium Embedded Framework.framework"
                self.path2basename(relpkgdir, CEF_framework)
                CEF_framework = self.dst_path_of(CEF_framework)

                if self.args.get('bugsplat'):
                    self.path2basename(relpkgdir, "BugsplatMac.framework")

            with self.prefix(dst="MacOS"):
                executable = self.dst_path_of(self.channel())
                if self.args.get('bugsplat'):
                    # According to Apple Technical Note TN2206:
                    # https://developer.apple.com/library/archive/technotes/tn2206/_index.html#//apple_ref/doc/uid/DTS40007919-CH1-TNTAG207
                    # "If an app uses @rpath or an absolute path to link to a
                    # dynamic library outside of the app, the app will be
                    # rejected by Gatekeeper. ... Neither the codesign nor the
                    # spctl tool will show the error."
                    # (Thanks, Apple. Maybe fix spctl to warn?)
                    # The BugsplatMac framework embeds @rpath, which is
                    # causing scary Gatekeeper popups at viewer start. Work
                    # around this by changing the reference baked into our
                    # viewer. The install_name_tool -change option needs the
                    # previous value. Instead of guessing -- which might
                    # silently be defeated by a BugSplat SDK update that
                    # changes their baked-in @rpath -- ask for the path
                    # stamped into the framework.
                    # Let exception, if any, propagate -- if this doesn't
                    # work, we need the build to noisily fail!
                    oldpath = subprocess.check_output(
                        ['objdump', '--macho', '--dylib-id', '--non-verbose',
                         os.path.join(relpkgdir, "BugsplatMac.framework", "BugsplatMac")]
                        ).splitlines()[-1]  # take the last line of output
                    self.run_command(
                        ['install_name_tool', '-change', oldpath,
                         '@executable_path/../Frameworks/BugsplatMac.framework/BugsplatMac',
                         executable])

                # NOTE: the -S argument to strip causes it to keep
                # enough info for annotated backtraces (i.e. function
                # names in the crash log). 'strip' with no arguments
                # yields a slightly smaller binary but makes crash
                # logs mostly useless. This may be desirable for the
                # final release. Or not.
                if ("package" in self.args['actions'] or 
                    "unpacked" in self.args['actions']):
                    self.run_command(
                        ['strip', '-S', executable])

            with self.prefix(dst="Resources"):
                # defer cross-platform file copies until we're in the
                # nested Resources directory
                super(DarwinManifest, self).construct()

                # need .icns file referenced by Info.plist
                with self.prefix(src=self.icon_path(), dst="") :
                    self.path("secondlife.icns")

                # Copy in the updater script and helper modules
                self.path(src=os.path.join(pkgdir, 'VMP'), dst="updater")

                with self.prefix(src="", dst=os.path.join("updater", "icons")):
                    self.path2basename(self.icon_path(), "secondlife.ico")
                    with self.prefix(src="vmp_icons", dst=""):
                        self.path("*.png")
                        self.path("*.gif")

                with self.prefix(src=relpkgdir, dst=""):
                    self.path("libndofdev.dylib")
                    self.path("libhunspell-*.dylib")   

                with self.prefix(src_dst="cursors_mac"):
                    self.path("*.tif")

                self.path("licenses-mac.txt", dst="licenses.txt")
                self.path("featuretable_mac.txt")
                self.path("cube.dae")
                self.path("SecondLife.nib")

                with self.prefix(src=pkgdir,dst=""):
                    self.path("ca-bundle.crt")

                # Translations
                self.path("English.lproj/language.txt")
                self.replace_in(src="English.lproj/InfoPlist.strings",
                                dst="English.lproj/InfoPlist.strings",
                                searchdict={'%%VERSION%%':'.'.join(self.args['version'])}
                                )
                self.path("German.lproj")
                self.path("Japanese.lproj")
                self.path("Korean.lproj")
                self.path("da.lproj")
                self.path("es.lproj")
                self.path("fr.lproj")
                self.path("hu.lproj")
                self.path("it.lproj")
                self.path("nl.lproj")
                self.path("pl.lproj")
                self.path("pt.lproj")
                self.path("ru.lproj")
                self.path("tr.lproj")
                self.path("uk.lproj")
                self.path("zh-Hans.lproj")

                def path_optional(src, dst):
                    """
                    For a number of our self.path() calls, not only do we want
                    to deal with the absence of src, we also want to remember
                    which were present. Return either an empty list (absent)
                    or a list containing dst (present). Concatenate these
                    return values to get a list of all libs that are present.
                    """
                    # This was simple before we started needing to pass
                    # wildcards. Fortunately, self.path() ends up appending a
                    # (source, dest) pair to self.file_list for every expanded
                    # file processed. Remember its size before the call.
                    oldlen = len(self.file_list)
                    try:
                        self.path(src, dst)
                        # The dest appended to self.file_list has been prepended
                        # with self.get_dst_prefix(). Strip it off again.
                        added = [os.path.relpath(d, self.get_dst_prefix())
                                 for s, d in self.file_list[oldlen:]]
                    except MissingError as err:
                        print("Warning: "+err.msg, file=sys.stderr)
                        added = []
                    if not added:
                        print("Skipping %s" % dst)
                    return added

                # dylibs is a list of all the .dylib files we expect to need
                # in our bundled sub-apps. For each of these we'll create a
                # symlink from sub-app/Contents/Resources to the real .dylib.
                # Need to get the llcommon dll from any of the build directories as well.
                libfile_parent = self.get_dst_prefix()
                dylibs=[]
                for libfile in (
                                "libapr-1.0.dylib",
                                "libaprutil-1.0.dylib",
                                "libexpat.1.dylib",
                                # libnghttp2.dylib is a symlink to
                                # libnghttp2.major.dylib, which is a symlink to
                                # libnghttp2.version.dylib. Get all of them.
                                "libnghttp2.*dylib",
                                "liburiparser.*dylib",
                                ):
                    dylibs += path_optional(os.path.join(relpkgdir, libfile), libfile)

                # SLVoice executable
                with self.prefix(src=os.path.join(pkgdir, 'bin', 'release')):
                    self.path("SLVoice")

                # Vivox libraries
                for libfile in (
                                'libortp.dylib',
                                'libvivoxsdk.dylib',
                                ):
                    self.path2basename(relpkgdir, libfile)

                # Fmod studio dylibs (vary based on configuration)
                if self.args['fmodstudio'] == 'ON':
                    if self.args['buildtype'].lower() == 'debug':
                        for libfile in (
                                    "libfmodL.dylib",
                                    ):
                            dylibs += path_optional(os.path.join(debpkgdir, libfile), libfile)
                    else:
                        for libfile in (
                                    "libfmod.dylib",
                                    ):
                            dylibs += path_optional(os.path.join(relpkgdir, libfile), libfile)

                # our apps
                executable_path = {}
                embedded_apps = [ (os.path.join("llplugin", "slplugin"), "SLPlugin.app") ]
                for app_bld_dir, app in embedded_apps:
                    self.path2basename(os.path.join(os.pardir,
                                                    app_bld_dir, self.args['configuration']),
                                       app)
                    executable_path[app] = \
                        self.dst_path_of(os.path.join(app, "Contents", "MacOS"))

                    # our apps dependencies on shared libs
                    # for each app, for each dylib we collected in dylibs,
                    # create a symlink to the real copy of the dylib.
                    with self.prefix(dst=os.path.join(app, "Contents", "Resources")):
                        for libfile in dylibs:
                            self.relsymlinkf(os.path.join(libfile_parent, libfile))

                # Dullahan helper apps go inside SLPlugin.app
                with self.prefix(dst=os.path.join(
                    "SLPlugin.app", "Contents", "Frameworks")):

                    frameworkname = 'Chromium Embedded Framework'

                    # This code constructs a relative symlink from the
                    # target framework folder back to the real CEF framework.
                    # It needs to be relative so that the symlink still works when
                    # (as is normal) the user moves the app bundle out of the DMG
                    # and into the /Applications folder. Note we pass catch=False,
                    # letting the uncaught exception terminate the process, since
                    # without this symlink, Second Life web media can't possibly work.

                    # It might seem simpler just to symlink Frameworks back to
                    # the parent of Chromimum Embedded Framework.framework. But
                    # that would create a symlink cycle, which breaks our
                    # packaging step. So make a symlink from Chromium Embedded
                    # Framework.framework to the directory of the same name, which
                    # is NOT an ancestor of the symlink.

                    # from SLPlugin.app/Contents/Frameworks/Chromium Embedded
                    # Framework.framework back to
                    # $viewer_app/Contents/Frameworks/Chromium Embedded Framework.framework
                    SLPlugin_framework = self.relsymlinkf(CEF_framework, catch=False)

                    # for all the multiple CEF/Dullahan (as of CEF 76) helper app bundles we need:
                    for helper in (
                        "DullahanHelper",
                        "DullahanHelper (GPU)",
                        "DullahanHelper (Renderer)",
                        "DullahanHelper (Plugin)",
                    ):
                        # app is the directory name of the app bundle, with app/Contents/MacOS/helper as the executable
                        app = helper + ".app"

                        # copy DullahanHelper.app
                        self.path2basename(relpkgdir, app)

                        # and fix that up with a Frameworks/CEF symlink too
                        with self.prefix(dst=os.path.join(
                                app, 'Contents', 'Frameworks')):
                            # from Dullahan Helper *.app/Contents/Frameworks/Chromium Embedded
                            # Framework.framework back to
                            # SLPlugin.app/Contents/Frameworks/Chromium Embedded Framework.framework
                            # Since SLPlugin_framework is itself a
                            # symlink, don't let relsymlinkf() resolve --
                            # explicitly call relpath(symlink=True) and
                            # create that symlink here.
                            helper_framework = \
                            self.symlinkf(self.relpath(SLPlugin_framework, symlink=True), catch=False)

                        # change_command includes install_name_tool, the
                        # -change subcommand and the old framework rpath
                        # stamped into the executable. To use it with
                        # run_command(), we must still append the new
                        # framework path and the pathname of the
                        # executable to change.
                        change_command = [
                            'install_name_tool', '-change',
                            '@rpath/Frameworks/Chromium Embedded Framework.framework/Chromium Embedded Framework']

                        with self.prefix(dst=os.path.join(
                                app, 'Contents', 'MacOS')):
                            # Now self.get_dst_prefix() is, at runtime,
                            # @executable_path. Locate the helper app
                            # framework (which is a symlink) from here.
                            newpath = os.path.join(
                                '@executable_path',
                                    self.relpath(helper_framework, symlink=True),
                                frameworkname)
                                # and restamp the Dullahan Helper executable itself
                            self.run_command(
                                change_command +
                                    [newpath, self.dst_path_of(helper)])

                # SLPlugin plugins
                with self.prefix(dst="llplugin"):
                    dylibexecutable = 'media_plugin_cef.dylib'
                    self.path2basename("../media_plugins/cef/" + self.args['configuration'],
                                       dylibexecutable)

                    # Do this install_name_tool *after* media plugin is copied over.
                    # Locate the framework lib executable -- relative to
                    # SLPlugin.app/Contents/MacOS, which will be our
                    # @executable_path at runtime!
                    newpath = os.path.join(
                        '@executable_path',
                        self.relpath(SLPlugin_framework, executable_path["SLPlugin.app"],
                                     symlink=True),
                        frameworkname)
                    # restamp media_plugin_cef.dylib
                    self.run_command(
                        change_command +
                        [newpath, self.dst_path_of(dylibexecutable)])

                    # copy LibVLC plugin itself
                    dylibexecutable = 'media_plugin_libvlc.dylib'
                    self.path2basename("../media_plugins/libvlc/" + self.args['configuration'], dylibexecutable)
                    # add @rpath for the correct LibVLC subfolder
                    self.run_command(['install_name_tool', '-add_rpath', '@loader_path/lib', self.dst_path_of(dylibexecutable)])

                    # copy LibVLC dynamic libraries
                    with self.prefix(src=relpkgdir, dst="lib"):
                        self.path( "libvlc*.dylib*" )
                        # copy LibVLC plugins folder
                        with self.prefix(src='plugins', dst=""):
                            self.path( "*.dylib" )
                            self.path( "plugins.dat" )

    def package_finish(self):
        global CHANNEL_VENDOR_BASE
        # MBW -- If the mounted volume name changes, it breaks the .DS_Store's background image and icon positioning.
        #  If we really need differently named volumes, we'll need to create multiple DS_Store file images, or use some other trick.

        volname=CHANNEL_VENDOR_BASE+" Installer"  # DO NOT CHANGE without understanding comment above

        imagename = self.installer_base_name()

        sparsename = imagename + ".sparseimage"
        finalname = imagename + ".dmg"
        # make sure we don't have stale files laying about
        self.remove(sparsename, finalname)

        self.run_command(['hdiutil', 'create', sparsename,
                          '-volname', volname, '-fs', 'HFS+',
                          '-type', 'SPARSE', '-megabytes', '1300',
                          '-layout', 'SPUD'])

        # mount the image and get the name of the mount point and device node
        try:
            hdi_output = subprocess.check_output(['hdiutil', 'attach', '-private', sparsename], text=True)
        except subprocess.CalledProcessError as err:
            sys.exit("failed to mount image at '%s'" % sparsename)
            
        try:
            devfile = re.search("/dev/disk([0-9]+)[^s]", hdi_output).group(0).strip()
            volpath = re.search('HFS\s+(.+)', hdi_output).group(1).strip()

            # Copy everything in to the mounted .dmg

            app_name = self.app_name()

            # Hack:
            # Because there is no easy way to coerce the Finder into positioning
            # the app bundle in the same place with different app names, we are
            # adding multiple .DS_Store files to svn. There is one for release,
            # one for release candidate and one for first look. Any other channels
            # will use the release .DS_Store, and will look broken.
            # - Ambroff 2008-08-20
            dmg_template = os.path.join(
                'installers', 'darwin', '%s-dmg' % self.channel_type())

            if not os.path.exists (self.src_path_of(dmg_template)):
                dmg_template = os.path.join ('installers', 'darwin', 'release-dmg')

            for s,d in list({self.get_dst_prefix():app_name + ".app",
                        os.path.join(dmg_template, "_VolumeIcon.icns"): ".VolumeIcon.icns",
                        os.path.join(dmg_template, "background.jpg"): "background.jpg",
                        os.path.join(dmg_template, "_DS_Store"): ".DS_Store"}.items()):
                print("Copying to dmg", s, d)
                self.copy_action(self.src_path_of(s), os.path.join(volpath, d))

            # Hide the background image, DS_Store file, and volume icon file (set their "visible" bit)
            for f in ".VolumeIcon.icns", "background.jpg", ".DS_Store":
                pathname = os.path.join(volpath, f)
                self.run_command(['SetFile', '-a', 'V', pathname])

            # Create the alias file (which is a resource file) from the .r
            self.run_command(
                ['Rez', self.src_path_of("installers/darwin/release-dmg/Applications-alias.r"),
                 '-o', os.path.join(volpath, "Applications")])

            # Set the alias file's alias and custom icon bits
            self.run_command(['SetFile', '-a', 'AC', os.path.join(volpath, "Applications")])

            # Set the disk image root's custom icon bit
            self.run_command(['SetFile', '-a', 'C', volpath])

            # Sign the app if requested; 
            # do this in the copy that's in the .dmg so that the extended attributes used by 
            # the signature are preserved; moving the files using python will leave them behind
            # and invalidate the signatures.
            if 'signature' in self.args:
                app_in_dmg=os.path.join(volpath,self.app_name()+".app")
                print("Attempting to sign '%s'" % app_in_dmg)
                identity = self.args['signature']
                if identity == '':
                    identity = 'Developer ID Application'

                # Look for an environment variable set via build.sh when running in Team City.
                try:
                    build_secrets_checkout = os.environ['build_secrets_checkout']
                except KeyError:
                    pass
                else:
                    # variable found so use it to unlock keychain followed by codesign
                    home_path = os.environ['HOME']
                    keychain_pwd_path = os.path.join(build_secrets_checkout,'code-signing-osx','password.txt')
                    keychain_pwd = open(keychain_pwd_path).read().rstrip()

                    # Note: As of macOS Sierra, keychains are created with
                    #       names postfixed with '-db' so for example, the SL
                    #       Viewer keychain would by default be found in
                    #       ~/Library/Keychains/viewer.keychain-db instead of
                    #       just ~/Library/Keychains/viewer.keychain in
                    #       earlier versions.
                    #
                    #       Because we have old OS files from previous
                    #       versions of macOS on the build hosts, the
                    #       configurations are different on each host. Some
                    #       have viewer.keychain, some have viewer.keychain-db
                    #       and some have both. As you can see in the line
                    #       below, this script expects the Linden Developer
                    #       cert/keys to be in viewer.keychain.
                    #
                    #       To correctly sign builds you need to make sure
                    #       ~/Library/Keychains/viewer.keychain exists on the
                    #       host and that it contains the correct cert/key. If
                    #       a build host is set up with a clean version of
                    #       macOS Sierra (or later) then you will need to
                    #       change this line (and the one for 'codesign'
                    #       command below) to point to right place or else
                    #       pull in the cert/key into the default viewer
                    #       keychain 'viewer.keychain-db' and export it to
                    #       'viewer.keychain'
                    viewer_keychain = os.path.join(home_path, 'Library',
                                                   'Keychains', 'viewer.keychain')
                    self.run_command(['security', 'unlock-keychain',
                                      '-p', keychain_pwd, viewer_keychain])
                    sign_retry_wait=15
                    resources = app_in_dmg + "/Contents/Resources/"
                    plain_sign = glob.glob(resources + "llplugin/*.dylib")
                    deep_sign = [
                        resources + "updater/SLVersionChecker",
                        resources + "SLPlugin.app/Contents/MacOS/SLPlugin",
                        app_in_dmg,
                        ]
                    for attempt in range(3):
                        if attempt: # second or subsequent iteration
                            print("codesign failed, waiting {:d} seconds before retrying".format(sign_retry_wait),
                                  file=sys.stderr)
                            time.sleep(sign_retry_wait)
                            sign_retry_wait*=2

                        try:
                            # Note: See blurb above about names of keychains
                            for signee in plain_sign:
                                self.run_command(
                                    ['codesign',
                                     '--force',
                                     '--timestamp',
                                     '--keychain', viewer_keychain,
                                     '--sign', identity,
                                     signee])
                            for signee in deep_sign:
                                self.run_command(
                                    ['codesign',
                                     '--verbose',
                                     '--deep',
                                     '--force',
                                     '--entitlements', self.src_path_of("slplugin.entitlements"),
                                     '--options', 'runtime',
                                     '--keychain', viewer_keychain,
                                     '--sign', identity,
                                     signee])
                            break # if no exception was raised, the codesign worked
                        except ManifestError as err:
                            # 'err' goes out of scope
                            sign_failed = err
                    else:
                        print("Maximum codesign attempts exceeded; giving up", file=sys.stderr)
                        raise sign_failed
                    self.run_command(['spctl', '-a', '-texec', '-vvvv', app_in_dmg])
                    self.run_command([self.src_path_of("installers/darwin/apple-notarize.sh"), app_in_dmg])

        finally:
            # Unmount the image even if exceptions from any of the above 
            self.run_command(['hdiutil', 'detach', '-force', devfile])

        print("Converting temp disk image to final disk image")
        self.run_command(['hdiutil', 'convert', sparsename, '-format', 'UDZO',
                          '-imagekey', 'zlib-level=9', '-o', finalname])
        # get rid of the temp file
        self.package_file = finalname
        self.remove(sparsename)


class Darwin_i386_Manifest(DarwinManifest):
    address_size = 32


class Darwin_i686_Manifest(DarwinManifest):
    """alias in case arch is passed as i686 instead of i386"""
    pass


class Darwin_x86_64_Manifest(DarwinManifest):
    address_size = 64


class LinuxManifest(ViewerManifest):
    build_data_json_platform = 'lnx'

    def construct(self):
        super(LinuxManifest, self).construct()

        pkgdir = os.path.join(self.args['build'], os.pardir, 'packages')
        if "package_dir" in self.args:
            pkgdir = self.args['package_dir']
        
        relpkgdir = os.path.join(pkgdir, "lib", "release")
        debpkgdir = os.path.join(pkgdir, "lib", "debug")

        self.path("licenses-linux.txt","licenses.txt")
        with self.prefix("linux_tools"):
            self.path("client-readme.txt","README-linux.txt")
            self.path("client-readme-voice.txt","README-linux-voice.txt")
            self.path("client-readme-joystick.txt","README-linux-joystick.txt")
            self.path("wrapper.sh","secondlife")
            with self.prefix(dst="etc"):
                self.path("handle_secondlifeprotocol.sh")
                self.path("register_secondlifeprotocol.sh")
                self.path("refresh_desktop_app_entry.sh")
                self.path("launch_url.sh")
            self.path("install.sh")

        with self.prefix(dst="bin"):
            self.path("secondlife-bin","do-not-directly-run-secondlife-bin")
            #self.path("../linux_crash_logger/linux-crash-logger","linux-crash-logger.bin")
            self.path2basename("../llplugin/slplugin", "SLPlugin")
            #this copies over the python wrapper script, associated utilities and required libraries, see SL-321, SL-322 and SL-323
            #with self.prefix(src="../viewer_components/manager", dst=""):
            #    self.path("*.py")

        # recurses, packaged again
        self.path("res-sdl")

        # We  copy ll_icon.BMP in CMakeLists.txt to newview/res-sdl and this will let the above self.path step take  care of copying
        # the correct branded icon
        # Get the icons based on the channel type
        icon_path = self.icon_path()
        #print("DEBUG: icon_path '%s'" % icon_path)
        with self.prefix(src=icon_path) :
            self.path("secondlife_256.png","secondlife_icon.png")
            with self.prefix(dst="res-sdl") :
                self.path("secondlife_256.BMP","ll_icon.BMP")

        # plugins
        with self.prefix(src=os.path.join(self.args['build'], os.pardir, 'media_plugins'), dst="bin/llplugin"):
            self.path("gstreamer10/libmedia_plugin_gstreamer10.so", "libmedia_plugin_gstreamer.so")
            self.path("cef/libmedia_plugin_cef.so", "libmedia_plugin_cef.so" )
        with self.prefix(src=os.path.join(pkgdir, 'lib', 'release'), dst="lib"):
            self.path( "libcef.so" )
        with self.prefix(src=os.path.join(pkgdir, 'lib', 'release', 'swiftshader'), dst=os.path.join("bin", "swiftshader") ):
            self.path( "*.so" )
        with self.prefix(src=os.path.join(pkgdir, 'lib', 'release', 'swiftshader'), dst=os.path.join("lib", "swiftshader") ):
            self.path( "*.so" )

        with self.prefix(src=os.path.join(pkgdir, 'bin', 'release'), dst="bin"):
            self.path( "chrome-sandbox" )
            self.path( "dullahan_host" )
            self.path( "snapshot_blob.bin" )
            self.path( "v8_context_snapshot.bin" )
        with self.prefix(src=os.path.join(pkgdir, 'bin', 'release'), dst="lib"):
            self.path( "snapshot_blob.bin" )
            self.path( "v8_context_snapshot.bin" )

        with self.prefix(src=os.path.join(pkgdir, 'resources'), dst="bin"):
            self.path( "chrome_100_percent.pak" )
            self.path( "chrome_200_percent.pak" )
            self.path( "resources.pak" )
            self.path( "icudtl.dat" )
        with self.prefix(src=os.path.join(pkgdir, 'resources'), dst="lib"):
            self.path( "chrome_100_percent.pak" )
            self.path( "chrome_200_percent.pak" )
            self.path( "resources.pak" )
            self.path( "icudtl.dat" )

        with self.prefix(src=os.path.join(pkgdir, 'resources', 'locales'), dst=os.path.join('bin', 'locales')):
            self.path("am.pak")
            self.path("ar.pak")
            self.path("bg.pak")
            self.path("bn.pak")
            self.path("ca.pak")
            self.path("cs.pak")
            self.path("da.pak")
            self.path("de.pak")
            self.path("el.pak")
            self.path("en-GB.pak")
            self.path("en-US.pak")
            self.path("es-419.pak")
            self.path("es.pak")
            self.path("et.pak")
            self.path("fa.pak")
            self.path("fi.pak")
            self.path("fil.pak")
            self.path("fr.pak")
            self.path("gu.pak")
            self.path("he.pak")
            self.path("hi.pak")
            self.path("hr.pak")
            self.path("hu.pak")
            self.path("id.pak")
            self.path("it.pak")
            self.path("ja.pak")
            self.path("kn.pak")
            self.path("ko.pak")
            self.path("lt.pak")
            self.path("lv.pak")
            self.path("ml.pak")
            self.path("mr.pak")
            self.path("ms.pak")
            self.path("nb.pak")
            self.path("nl.pak")
            self.path("pl.pak")
            self.path("pt-BR.pak")
            self.path("pt-PT.pak")
            self.path("ro.pak")
            self.path("ru.pak")
            self.path("sk.pak")
            self.path("sl.pak")
            self.path("sr.pak")
            self.path("sv.pak")
            self.path("sw.pak")
            self.path("ta.pak")
            self.path("te.pak")
            self.path("th.pak")
            self.path("tr.pak")
            self.path("uk.pak")
            self.path("vi.pak")
            self.path("zh-CN.pak")
            self.path("zh-TW.pak")

        self.path("featuretable_linux.txt")
        self.path("cube.dae")

        with self.prefix(src=pkgdir, dst="bin"):
            self.path("ca-bundle.crt")

    def package_finish(self):
        installer_name = self.installer_base_name()

        self.strip_binaries()

        # Fix access permissions
        self.run_command(['find', self.get_dst_prefix(),
                          '-type', 'd', '-exec', 'chmod', '755', '{}', ';'])
        for old, new in ('0700', '0755'), ('0500', '0555'), ('0600', '0644'), ('0400', '0444'):
            self.run_command(['find', self.get_dst_prefix(),
                              '-type', 'f', '-perm', old,
                              '-exec', 'chmod', new, '{}', ';'])

        realname = self.get_dst_prefix()
        tempname = self.build_path_of(installer_name)
        if "FLATPAK_DEST" in os.environ:
            flatpakDest = os.environ["FLATPAK_DEST"] 
            print( "Moving result into %s" % flatpakDest )
            shutil.move( realname, "%s/viewer" % flatpakDest ) 
            self.package_file = flatpakDest
            return
            
        self.package_file = installer_name + '.tar.bz2'

        # temporarily move directory tree so that it has the right
        # name in the tarfile
        self.run_command(["mv", realname, tempname])
        try:
            # only create tarball if it's a release build.
            if self.args['buildtype'].lower() == 'release':
                # --numeric-owner hides the username of the builder for
                # security etc.
                self.run_command(['tar', '-C', self.get_build_prefix(),
                                  '--numeric-owner', '-cjf',
                                 tempname + '.tar.bz2', installer_name])
            else:
                print("Skipping %s.tar.bz2 for non-Release build (%s)" % \
                      (installer_name, self.args['buildtype']))
        finally:
            self.run_command(["mv", tempname, realname])

    def strip_binaries(self):
        doStrip = False
        if self.args['buildtype'].lower() == 'release' and self.is_packaging_viewer():
            doStrip = True
        # In case of flatpak flatpak-build will call strip, disable doStrip here to get a flatpak symbol package. Increases flatpak size by about 1G
        if "FLATPAK_DEST" in os.environ:
            doStrip = True

        if doStrip:
            print("* Going strip-crazy on the packaged binaries, since this is a Release build")
            # makes some small assumptions about our packaged dir structure
            self.run_command(
                ["find"] +
                [os.path.join(self.get_dst_prefix(), dir) for dir in ('bin', 'lib')] +
                ['-type', 'f', '!', '-name', '*.py',
                 '!', '-name', '*.pak',
                 '!', '-name', '*.bin',
                 '!', '-name', '*.dat',
                 '!', '-name', '*.crt',
                 '!', '-name', '*.dll',
                 '!', '-name', '*.lib',
                 '!', '-name', 'update_install', '-exec', 'strip', '-S', '{}', ';'])

class Linux_x86_64_Manifest(LinuxManifest):
    address_size = 64

    def construct(self):
        super(Linux_x86_64_Manifest, self).construct()

        # support file for valgrind debug tool
        self.path("secondlife-i686.supp")

        pkgdir = os.path.join(self.args['build'], os.pardir, 'packages')
        if "package_dir" in self.args:
            pkgdir = self.args['package_dir']

        relpkgdir = os.path.join(pkgdir, "lib", "release")
        debpkgdir = os.path.join(pkgdir, "lib", "debug")
        with self.prefix(src=relpkgdir, dst="lib"):
            self.path("libapr-1.so")
            self.path("libapr-1.so.0")
            self.path("libapr-1.so.0.4.5")
            self.path("libaprutil-1.so")
            self.path("libaprutil-1.so.0")
            self.path("libaprutil-1.so.0.4.1")
            self.path("libexpat.so.*")
            self.path("libSDL*.so.*")

            self.path("libjemalloc*.so")

            self.path("libhunspell-1.3.so*")
            self.path("libalut.so*")
            self.path("libopenal.so*")
            self.path("libopenal.so", "libvivoxoal.so.1") # vivox's sdk expects this soname
            if self.args['fmodstudio'] == 'ON':
                try:
                    self.path("libfmod.so.11.7")
                    self.path("libfmod.so.11")
                    self.path("libfmod.so")
                    pass
                except:
                    print("Skipping libfmod.so - not found")
                    pass

        with self.prefix(src=os.path.join(pkgdir, 'bin32' ), dst="bin"):
            self.path("SLVoice")
        with self.prefix(src=os.path.join(pkgdir ), dst="bin"):
            self.path("win32")
            self.path("win64")

        with self.prefix(src=os.path.join(pkgdir, 'lib32' ), dst="lib32"):
            self.path("libsnd*")
            self.path("libvivox*")
            self.path("libortp*")
            self.path("*.crt")
 
        self.strip_binaries()
################################################################

if __name__ == "__main__":
    # Report our own command line so that, in case of trouble, a developer can
    # manually rerun the same command.
    print(('%s \\\n%s' %
          (sys.executable,
           ' '.join((("'%s'" % arg) if ' ' in arg else arg) for arg in sys.argv))))
    # fmodstudio and openal can be used simultaneously and controled by environment
    extra_arguments = [
        dict(name='bugsplat', description="""BugSplat database to which to post crashes,
             if BugSplat crash reporting is desired""", default=''),
        dict(name='fmodstudio', description="""Indication if fmod studio libraries are needed""", default='OFF'),
        dict(name='openal', description="""Indication openal libraries are needed""", default='OFF'),
        ]
    try:
        main(extra=extra_arguments)
    except (ManifestError, MissingError) as err:
        sys.exit("\nviewer_manifest.py failed: "+err.msg)
    except:
        raise
