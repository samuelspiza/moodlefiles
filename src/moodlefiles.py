# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2010, Samuel Spiza
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Moodle Files

Downloads and updates files from the Moodle platform.

[Moodle Files](http://github.com/samuelspiza/moodlefiles) is hosted on Github.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__copyright__ = "Copyright (c) 2009-2010, Samuel Spiza"
__license__ = "Simplified BSD License"
__version__ = "0.1.1"
__all__ = ["moodleLogin","openModule"]

import re
import os
from BeautifulSoup import BeautifulSoup
from fileupdater import safe_getResponse, File

def moodleLogin(user, password):
    """Logs the user into the moodle system."""
    # CAS URLs
    casUrl = 'https://cas.uni-duisburg-essen.de/cas/login'
    casSvc = "http://moodle.uni-duisburg-essen.de/login/index.php?authCAS=CAS"

    # Get token
    data = safe_getResponse(casUrl).read()
    regexp = '<input type="hidden" name="lt" value="([A-Za-z0-9_\-]*)" />'
    token = re.search(regexp, data, re.MULTILINE).group(1)

    # Login
    postData = {'username': user, 'password': password,
                'lt': token, '_eventId': 'submit'}
    safe_getResponse(casUrl + '?service=' + casSvc, postData)

def openModule(moduleName, url, overrides=[], test=False):
    """Downloads and updates all files for a module."""
    content = safe_getResponse(url).read()
    soup = BeautifulSoup(content)
    links = soup.findAll(attrs={'href' : re.compile("resource/view.php")})
    for link in links:
        if not link.span is None:
            download(link['href'], moduleName, overrides, test=test)

def download(url, moduleName, overrides, test=False):
    """Downloads files recursively."""
    response = safe_getResponse(url)
    if response is not None:
        contentType = response.info().get("Content-Type")

        # Skip download of unsupported content types
        unsupportedContentTypes = ["audio/x-pn-realaudio"]
        for ct in unsupportedContentTypes:
            if contentType.startswith(ct):
                return

        if not contentType.startswith('text/html'):
            # Direct download
            saveFile(response.geturl(), moduleName, overrides, test=test)

        else:
            # Indirect download or recursion
            content = response.read()
            soup = BeautifulSoup(content)

            # Frames
            regobj = re.compile("http://moodle.uni-duisburg-essen.de/file.php")
            frames = soup.findAll(attrs={'src' : regobj})
            for f in frames:
                saveFile(f['src'], moduleName, overrides, test=test)

            # Files
            regobj = re.compile("http://moodle.uni-duisburg-essen.de/file.php")
            files = soup.findAll(attrs={'href' : regobj})
            for f in files:
                saveFile(f['href'], moduleName, overrides, test=test)

            # Dirs
            dirs = soup.findAll(attrs={'href' : re.compile("subdir")})
            for d in dirs:
                baseurl = "http://moodle.uni-duisburg-essen.de/mod/resource/"
                href = baseurl + d['href']
                download(href, moduleName, overrides, test=test)

            # PopUp links
            popup = soup.find(attrs={'href' : re.compile("inpopup=true")})
            if popup is not None:
                download(popup['href'], moduleName, overrides, test=test)

def saveFile(url, moduleName, overrides, test=False):
    """Saves or updates the file localy."""
    local = buildLocalFilePath(url, moduleName, overrides)
    # Update file and return if the local file was modified
    return File(url, local, test=test).update()

def buildLocalFilePath(url, moduleName, overrides):
    """Build the path of the local file.
    
    Takes the the tail from the URL after 'file.php', goes through the list of
    overrides and uses the first that applies to the file to build the local
    filepath. If no override applies to the file, it will be placed in the
    subdirectory 'stuff'.
    """
    newpath = "/".join(url.split("/")[5:])
    newpath = newpath.replace("?forcedownload=1", "")
    for o in overrides.values():
        if (not 'regexp' in o or re.search(o['regexp'], newpath) is not None) \
            and (not 'remote' in o or newpath.startswith(o['remote'])):
            # Strip the remote directory from the new path
            if 'remote' in o:
                newpath = newpath.replace(o['remote'] + "/", "")
            return os.path.join(moduleName, o['folder'], newpath)
    # Use subdirectory 'stuff' if nothing matched
    return os.path.join(moduleName, "stuff", newpath)
