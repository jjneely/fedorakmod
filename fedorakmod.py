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

import rpm
from sets import Set

from rpmUtils.miscutils import *
from yum import packages
from yum.constants import TS_INSTALL
from yum.plugins import TYPE_CORE, PluginYumExit

requires_api_version = '2.4'
plugin_type = (TYPE_CORE,)

kernelProvides = Set([ "kernel-%s" % a for a in rpmUtils.arch.arches.keys() ])
        

def flagToString(flags):
    # <shoving something pointy in my eye>
    if flags & rpm.RPMSENSE_EQUAL & rpm.RPMSENSE_GREATER:
        return 'GE'
    if flags & rpm.RPMSENSE_EQUAL & rpm.RPMSENSE_LESS:
        return 'LE'
    if flags & rpm.RPMSENSE_EQUAL:
        return 'EQ'
    if flags & rpm.RPMSENSE_GREATER:
        return 'GT'
    if flags & rpm.RPMSENSE_LESS:
        return 'LT'
    # </shoving something pointy in my eye>

    # Umm...now I'm screwed
    return flags


def populatePrco(po, hdr):
    "Populate the package object with the needed PRCO interface."
    # Apperently, Yum actually never takes the hdr object and uses it
    # to populate the prco information

    # prco['foo'] looks like (name, flag, (e,v,r))
    for tag in ['OBSOLETE', 'CONFLICT', 'REQUIRE', 'PROVIDE']:
        name = hdr[getattr(rpm, 'RPMTAG_%sNAME' % tag)]

        list = hdr[getattr(rpm, 'RPMTAG_%sFLAGS' % tag)]
        flag = [ flagToString(i) for i in list ]

        list = hdr[getattr(rpm, 'RPMTAG_%sVERSION' % tag)]
        vers = [ stringToVersion(i) for i in list ]

        prcotype = tag.lower() + 's'
        if name is not None:
            po.prco[prcotype] = zip(name, flag, vers)
        else:
            po.prco[prcotype] = []

    return po


def package(c, tuple):
    rpmdb = c.getRpmDB()

    # XXX: When RPM leaves dup NEVRA's??
    hdr = rpmdb.returnHeaderByTuple(tuple)[0]
    po = packages.YumInstalledPackage(hdr)
    populatePrco(po, hdr)

    return po

    
def whatProvides(c, list):
    """Return a list of POs of installed kernels."""

    bag = {}
    
    rpmdb = c.getRpmDB()
    for i in list:
        list = rpmdb.whatProvides(i, None, None)
        for p in list:
            bag[p] = package(c, p)

    return bag


def getInstalledKernels(c):
    return whatProvides(c, kernelProvides)


def getInstalledModules(c):
    return whatProvides(c, ["kernel-modules"])


def getKernelReqs(po):
    """Pass in a package header.  This function will return a list of
       tuples (name, flags, ver) representing any kernel requires."""
      
    reqs = po.returnPrco("requires")
    return filter(lambda r: r[0] in kernelProvides, reqs)


def installKernelModules(c, newKernelModules):
    """Figure out what special magic needs to be done to install/upgrade
       this kernel module.  This doesn't actually initiate an install
       as the module is already in the package sack to be applied."""

    for modpo in newKernelModules.values():
        c.info(4, "Installing kernel module: %s" % modpo.name)

        rpmdb = c.getRpmDB()
        tsInfo = c.getTsInfo()
    
        kernelReqs = getKernelReqs(modpo)
        instPkgs = rpmdb.returnTupleByKeyword(name=modpo.name)
        for pkg in instPkgs:
            po = package(c, pkg)
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


def pinKernels(c, kernels, kernel_modules):
    pass


def tsCheck(te):
    "Make sure this transaction element is sane."

    if te.ts_state == 'u':
        te.ts_state = 'i'
        te.output_state = TS_INSTALL


def init_hook(c):
    c.info(3, "Loading Fedora Extras kernel module support.")

    
def postresolve_hook(c):

    newKernelModules = {}
    newKernels = {}

    installedKernels = getInstalledKernels(c)

    for te in c.getTsInfo().getMembers():
        if te.ts_state not in ('i', 'u'):
            continue
        if "kernel-modules" in te.po.getProvidesNames():
            tsCheck(te)  # We do this here as I can't get the TE from the PO
            newKernelModules[te.po.returnPackageTuple()] = te.po
        if kernelProvides.intersection(te.po.getProvidesNames()) is not []:
            # We have a kernel package
            newKernels[te.po.returnPackageTuple()] = te.po

    # Pin kernels
    pinKernels(c, newKernels, newKernelModules)

    # Upgrade/Install kernel modules
    installKernelModules(c, newKernelModules)
           
# vim:ts=4:expandtab 
