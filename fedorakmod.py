#!/usr/bin/python

# fedorakmod.py - Fedora Extras Yum Kernel Module Support
# Copyright 2006 Jack Neely 
# Written by Jack Neely <jjneely@gmail.com>
#
# SDG
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import rpm
import rpmUtils
import packages

from yum.plugins import TYPE_CORE, PluginYumExit
# from yum.packages import YumInstalledPackage

requires_api_version = '2.1'
plugin_type = (TYPE_CORE,)

kernelsProvides = ["kernel-%s" % a for a in rpmUtils.arch.arches.keys()]

def getKernelReqs(hdr):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel requires."""
       
    # All po types don't support the same interface...fake it
    # XXX: What about using po.returnPrco() here?  What POs messed that up?
    reqs = []
    names = hdr[rpm.RPMTAG_REQUIRENAME]
    flags = hdr[rpm.RPMTAG_REQUIREFLAGS]
    ver =   hdr[rpm.RPMTAG_REQUIREVERSION]
    if names is not None:
        reqs = zip(names, flags, ver)
    return filter(lambda r: r[0] in kernelPovides, reqs)


def handleKernelModule(c, txmbr):
    """Figure out what special magic needs to be done to install/upgrade
       this kernel module."""

    # XXX: Lets try to fix this up so we don't need RPM header objects

    rpmdb = c.getRpmDB()
    tsInfo = c.getTsInfo()
    
    kernelReqs = getKernelReqs(txmbr.po.returnLocalHeader())
    instPkgs = rpmdb.returnTupleByKeyword(name=txmbr.po.name)
    for pkg in instPkgs:
        hdr = rpmdb.returnHeaderByTuple(pkg)[0] # XXX: name only?
        instKernelReqs = getKernelReqs(hdr)

        for r in kernelReqs:
            if r in instKernelReqs:
                # we know that an incoming kernel module requires the
                # same kernel as an already installed moulde of the
                # same name.  "Upgrade" this module instead of install
                po = packages.YumInstalledPackage(hdr)
                tsInfo.addErase(po)
                c.info(4, 'Removing kernel module %s upgraded to %s' %
                       (po, txmbr.po))
                break


def init_hook(c):
    c.info(3, "Loading Fedora Extras kernel module support.")

    
def postresolve_hook(c):
    for te in c.getTsInfo().getMembers():
        if te.ts_state not in ('i', 'u'):
            continue
        if "kernel-module" in te.po.getProvidesNames():
            c.info(4, "Handling kernel module: %s" % te.name)
            handleKernelModule(c, te)
            
