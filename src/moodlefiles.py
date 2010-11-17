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
__version__ = "0.2"
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

class Module:
    def __init__(self, moduleName, url, overrides=[], defaultDir=".",
                 test=False):
        self.name       = moduleName
        self.url        = url
        self.overrides  = overrides
        self.defaultDir = defaultDir
        self.test       = test

    def start(self):
        """Downloads and updates all files for a module."""
        content = safe_getResponse(self.url).read()
        soup = BeautifulSoup(content)
        links = soup.findAll(attrs={'href' : re.compile("resource/view.php")})
        for link in links:
            if not link.span is None:
                self.download(link['href'])

    def download(self, url):
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
                self.saveFile(response.geturl())

            else:
                # Indirect download or recursion
                content = response.read()
                soup = BeautifulSoup(content)

                # Frames
                regexp = "http://moodle.uni-duisburg-essen.de/file.php"
                frames = soup.findAll(attrs={'src' : re.compile(regexp)})
                for f in frames:
                    self.saveFile(f['src'])

                # Files
                regexp = "http://moodle.uni-duisburg-essen.de/file.php"
                files = soup.findAll(attrs={'href' : re.compile(regexp)})
                for f in files:
                    self.saveFile(f['href'])

                # Dirs
                dirs = soup.findAll(attrs={'href' : re.compile("subdir")})
                for d in dirs:
                    base = "http://moodle.uni-duisburg-essen.de/mod/resource/"
                    href = base + d['href']
                    self.download(href)

                # PopUp links
                popup = soup.find(attrs={'href' : re.compile("inpopup=true")})
                if popup is not None:
                    self.download(popup['href'])

    def saveFile(self, url):
        """Saves or updates the file localy."""
        local = self.buildLocalFilePath(url)
        if local is None:
            return False
        else:
            # Update file and return if the local file was modified
            return File(url, local, test=self.test).update()

    def buildLocalFilePath(self, url):
        """Build the path of the local file.
        
        Takes the the tail from the URL after 'file.php', goes through the list
        of overrides and uses the first that applies to the file to build the
        local filepath. If no override applies to the file, it will be placed
        in the subdirectory 'stuff'. Returns None if the override dosen't
        specify a 'folder' which means that the file should not be downloaded.
        """
        newpath = "/".join(url.split("/")[5:])
        newpath = newpath.replace("?forcedownload=1", "")
        for o in self.overrides.values():
            if (not 'regexp' in o \
                or re.search(o['regexp'], newpath) is not None) \
                and (not 'remote' in o or newpath.startswith(o['remote'])):
                # Strip the remote directory from the new path
                if 'remote' in o:
                    newpath = newpath.replace(o['remote'] + "/", "")
                if 'folder' in o:
                    return os.path.normpath(
                               os.path.join(self.name, o['folder'], newpath))
                else:
                    return None
        # Use subdirectory 'stuff' if nothing matched
        return os.path.normpath(
                   os.path.join(self.name, self.defaultDir, newpath))
