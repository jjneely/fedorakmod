#!/usr/bin/python

# fedorakmod.py - Fedora Extras Yum Kernel Module Support
# Copyright 2006 NC State University
# Written by Jack Neely <jjneely@ncsu.edu>
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

from sets import Set

import rpmUtils
from yum import packages
from yum.constants import TS_INSTALL
from yum.plugins import TYPE_CORE, PluginYumExit

requires_api_version = '2.4'
plugin_type = (TYPE_CORE,)

kernelProvides = Set([ "kernel-%s" % a for a in rpmUtils.arch.arches.keys() ])
        

def package(c, tuple):
    rpmdb = c.getRpmDB()

    # XXX: When RPM leaves dup NEVRA's??
    hdr = rpmdb.returnHeaderByTuple(tuple)[0]
    po = packages.YumInstalledPackage(hdr)
    return po

    
def whatProvides(c, list):
    """Return a list of POs of installed kernels."""

    bag = {}
    
    rpmdb = c.getRpmDB()
    for i in list:
        tuples = rpmdb.whatProvides(i, None, None)
        for p in tuples:
            bag[p] = package(c, p)

    return bag


def getInstalledKernels(c):
    return whatProvides(c, kernelProvides)


def getInstalledModules(c):
    return whatProvides(c, ["kernel-modules"])


def getKernelStuffs(po, match):
      
    reqs = po.returnPrco(match)
    return filter(lambda r: r[0] in kernelProvides, reqs)


def getKernelProvides(po):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel provides.
       Assumed that the PO is a kernel package."""
     
    return getKernelStuffs(po, "provides")


def getKernelReqs(po):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel requires."""
      
    return getKernelStuffs(po, "requires")


def mapNameToKernel(packageDict):
    # name -> (name, flag, (e,v,r)) where name is 'kernel-<arch>'
    modnames = {}
    for key in packageDict.keys():
        kernelReqs = getKernelReqs(packageDict[key])
        if modnames.has_key(key[0]):
            modnames[key[0]].extend(kernelReq)
        else:
            modnames[key[0]] = kernelReqs

    return modnames


def installKernelModules(c, newModules, installedModules):
    """Figure out what special magic needs to be done to install/upgrade
       this kernel module.  This doesn't actually initiate an install
       as the module is already in the package sack to be applied."""

    tsInfo = c.getTsInfo()

    for pktuple in newModules.keys():
        modpo = newModules[pktuple]
        c.info(4, "Installing kernel module: %s" % modpo.name)
        te = tsInfo.getMembers(pktuple)
        tsCheck(te)

        kernelReqs = getKernelReqs(modpo)
        instPkgs = filter(lambda p: p[0] == modpo.name,
                          installedModules.keys())
        for pkg in instPkgs:
            po = installedModules[pkg]
            instKernelReqs = getKernelReqs(po)

            for r in kernelReqs:
                if r in instKernelReqs:
                    # we know that an incoming kernel module requires the
                    # same kernel as an already installed moulde of the
                    # same name.  "Upgrade" this module instead of install.
                    tsInfo.addErase(po)
                    c.info(2, 'Removing kernel module %s upgraded to %s' %
                           (po, modpo))
                    break


def pinKernels(c, newKernels, newModules, installedModules):
    """If we are using kernel modules, do not upgrade/install a new 
       kernel until matching modules are available."""
    
    if len(newKernels.keys()) == 0:
        return

    tsInfo = c.getTsInfo()

    # name -> (name, flag, (e,v,r)) where name is 'kernel-<arch>'
    installedMap = mapNameToKernel(installedModules)
    newMap = mapNameToKernel(newModules)

    for kernel in newKernels.keys():
        # Each kernel should only provide one kernel-<arch>
        prov = getKernelProvides(newKernels[kernel])[0]

        for name in installedMap:
            if prov in installedMap[name]:
                # matching module already installed
                continue
            elif newMap.has_key(name) and prov in newMap[name]:
                # matching module available
                continue
            else:
                # No matching module for new kernel
                c.info(2, "Removing kernel %s from install set" % str(kernel))
                tsInfo.remove(kernel)
                del newKernels[kernel]


def sortByName(modules):
    names = {}
    for pktuple in modules.keys():
        prov = modules[pktuple].getProvidesNames()
        for p in prov:
            if p.endswith("-kmod"):
                name = p[:-5]
                if names.has_key(name):
                    names[name].append(pktuple)
                else:
                    names[name] = [pktuple]
                break

    return names


def availableModules(c, avaModules, newModules, installedModules, 
                     newKernels, installedKernels):

    for pktuple in avaModules:
        if installedModules.has_key(pktuple):
            del avaModules[pktuple]
        elif newModules.has_key(pktuple):
            del avaModules[pktuple]

    # Group kmods by name
    names = sortByName(newModules)
    

def tsCheck(te):
    "Make sure this transaction element is sane."

    if te.ts_state == 'u':
        te.ts_state = 'i'
        te.output_state = TS_INSTALL


def init_hook(c):
    c.info(3, "Loading Fedora Extras kernel module support.")

    
def postresolve_hook(c):

    avaModules = {}
    newModules = {}
    newKernels = {}

    installedKernels = getInstalledKernels(c)
    installedModules = getInstalledModules(c)

    for te in c.getTsInfo().getMembers():
        if te.ts_state == 'a' and "kernel-modules" in te.po.getProvidesNames():
            avaModules[te.po.returnPackageTuple()] = te.po
        if te.ts_state not in ('i', 'u'):
            continue
        if "kernel-modules" in te.po.getProvidesNames():
            newModules[te.po.returnPackageTuple()] = te.po
        if kernelProvides.intersection(te.po.getProvidesNames()) != Set([]):
            # We have a kernel package
            newKernels[te.po.returnPackageTuple()] = te.po

    # Pin kernels
    if c.confInt('main', 'pinkernels', default=0) is not 0:
        pinKernels(c, newKernels, newModules, installedModules)

    # Install modules for all kernels
    availableModules(c, avaModules, newModules, installedModules, newKernels,
                     installedKernels)

    # Upgrade/Install kernel modules
    installKernelModules(c, newModules, installedModules)
           
# vim:ts=4:expandtab 
