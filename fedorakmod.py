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
from rpmUtils.miscutils import compareEVR
from yum import packages
from yum.constants import TS_INSTALL
from yum.plugins import TYPE_CORE, PluginYumExit

requires_api_version = '2.4'
plugin_type = (TYPE_CORE,)

kernelProvides = Set([ "kernel-%s" % a for a in rpmUtils.arch.arches.keys() ])
        

def _whatProvides(c, list):
    """Return a list of POs of installed kernels."""

    bag = []
    
    rpmdb = c.getRpmDB()
    for i in list:
        tuples = rpmdb.whatProvides(i, None, None)
        for p in tuples:
            hdr = rpmdb.returnHeaderByTuple(tuple)[0]
            bag.append(packages.YumInstalledPackage(hdr))

    return bag


def _getKernelDeps(po, match):
      
    reqs = po.returnPrco(match)
    return [ r[0] for r in reqs if r[0] in kernelProvides ]
    #return filter(lambda r: r[0] in kernelProvides, reqs)


def getInstalledKernels(c):
    return _whatProvides(c, kernelProvides)


def getInstalledModules(c):
    return _whatProvides(c, ["kernel-modules"])


def getKernelProvides(po):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel provides.
       Assumed that the PO is a kernel package."""
     
    return _getKernelDeps(po, "provides")


def getKernelReqs(po):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel requires."""
      
    return _getKernelDeps(po, "requires")


def resolveVersions(packageList):
    """The packageDict is a dict of pkgtuple -> PO
       We return a dict of kernel version -> list of kmod POs
          where the list contains only one PO for each kmod name"""

    dict = {}
    for po in packageList:
        kernel = getKernelReqs(po)
        if len(kernel) == 1:
            kernel = kernel[0]
        else:
            print "Bad kmod package: May only require one kernel"
            continue

        if not dict.has_key(kernel):
            dict[kernel] = [po]
        else:
            sameName = [ x for x in dict[kernel] if x.name == po.name ][0]
            if compareEVR(sameName.returnEVR(), po.returnEVR()) < 0:
                dict[kernel].remove(sameName)
                dict[kernel].append(po)

    return dict


def installKernelModules(c, newModules, installedModules):
    """Figure out what special magic needs to be done to install/upgrade
       this kernel module.  This doesn't actually initiate an install
       as the module is already in the package sack to be applied."""

    tsInfo = c.getTsInfo()

    for modpo in newModules:
        c.info(4, "Installing kernel module: %s" % modpo.name)
        te = tsInfo.getMembers(modpo.returnPackageTuple())
        tsCheck(te)

        kernelReqs = getKernelReqs(modpo)
        instPkgs = filter(lambda p: p.name == modpo.name, installedModules)
        for po in instPkgs:
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


def pinKernels(c, newKernels, modules):
    """If we are using kernel modules, do not upgrade/install a new 
       kernel until matching modules are available."""
    
    table = resolveVersions(modules)
    names = Set([po.name for po in modules if po.name not in locals()['_[1]']])

    for kpo in newKernels:
        prov = getKernelProvides(kpo)[0]
        kmods = [po.name for po in table[prov]]
        if Set(kmods) != names:
            c.info(2, "Removing kernel %s from install set" % str(kernel))
            c.getTsInfo().remove(kpo)


def installAllKmods(c, avaModules, modules, kernels):
    list = []
    for po in avaModules:
        if po.returnPackageTuple() in [m.returnPackageTuple() for m in modules]:
            avaModules.remove(po)

    names = [ po.name for po in modules ]
    interesting = [ po.name for po in avaModules if po.name in names ]
    table = resolveVersions(interesting + modules)
    
    for kernel in [ getKernelProvides(k)[0] for k in kernels ]:
        if not table.has_key(kernel): continue
        for po in table[kernel]:
            if po not in modules:
                c.getTsInfo().addTrueInstall(po)
                list.append(po)

    return list


def tsCheck(te):
    "Make sure this transaction element is sane."

    if te.ts_state == 'u':
        te.ts_state = 'i'
        te.output_state = TS_INSTALL


def init_hook(c):
    c.info(3, "Loading Fedora Extras kernel module support.")

    
def postresolve_hook(c):

    avaModules = []
    newModules = []
    newKernels = []

    installedKernels = getInstalledKernels(c)
    installedModules = getInstalledModules(c)

    for te in c.getTsInfo().getMembers():
        if te.ts_state == 'a' and "kernel-modules" in te.po.getProvidesNames():
            avaModules.append(te.po)
        if te.ts_state not in ('i', 'u'):
            continue
        if "kernel-modules" in te.po.getProvidesNames():
            newModules.append(te.po)
        if kernelProvides.intersection(te.po.getProvidesNames()) != Set([]):
            newKernels.append(te.po)

    # Install modules for all kernels
    if c.confInt('main', 'installforallkernels', default=1) != 0:
        moreModules = installAllKmods(c, avaModules, 
                                      newModules + installedModules,
                                      newKernels + installedKernels)
        newModules = newModules + moreModules

    # Pin kernels
    if c.confInt('main', 'pinkernels', default=0) != 0:
        pinKernels(c, newKernels, newModules, installedModules)

    # Upgrade/Install kernel modules
    installKernelModules(c, newModules, installedModules)
           
# vim:ts=4:expandtab 
