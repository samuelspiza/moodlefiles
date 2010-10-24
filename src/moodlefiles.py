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
"""moodlefiles - a package to access moodle files in python"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__copyright__ = "Copyright (c) 2009-2010, Samuel Spiza"
__license__ = "Simplified BSD License"
__version__ = "0.1a"
__all__ = ["moodleLogin","openCourse"]

import re
import os
from BeautifulSoup import BeautifulSoup
from fileupdater import safe_getResponse, File

def moodleLogin(config):
    # Benutzerdaten
    password = config.get("moodle-credentials", "password") # PASSWORD
    user = config.get("moodle-credentials", "user")
    # CAS Daten
    casUrl = 'https://cas.uni-duisburg-essen.de/cas/login'
    casService = "http://moodle.uni-duisburg-essen.de/login/index.php?authCAS=CAS"
        
    # Get token
    data = safe_getResponse(casUrl).read()
    rawstr = '<input type="hidden" name="lt" value="([A-Za-z0-9_\-]*)" />'
    token = re.search(rawstr, data, re.MULTILINE).group(1)
    
    # Login
    postData = {'username': user, 'password': password, 'lt': token, '_eventId': 'submit'}
    safe_getResponse(casUrl + '?service=' + casService, postData)
    
    # Use the Service
    url = 'http://moodle.uni-duisburg-essen.de/index.php'
    # verueckt, erst muss ich einen kurs aufrufen um in der hauptseite eingeloggt zu sein
    safe_getResponse("http://moodle.uni-duisburg-essen.de/course/view.php?id=2064")
    
    safe_getResponse(url).read()
        

def openCourse(config, url, name, overrides=[]):
    print "Kurs:", name
    new_files = []
    html = safe_getResponse(url).read()
    soup = BeautifulSoup(html)
    links = soup.findAll(attrs={'href' : re.compile("resource/view.php")})
    for link in links:
        if not(link.span is None):
            new = download(config, link['href'], link.span.next, name, overrides)
            new_files.extend(new)
    return new_files

def download(config, url, name, CourseName, overrides):
    #print url
    new_files = []
    response = safe_getResponse(url)
    if(response is not None):
        # Direkter Download
        if(response.info().get("Content-Type").find('audio/x-pn-realaudio') == 0):
            d="" #print "Real Player Moodle Page"
        elif(response.info().get("Content-Type").find('text/html') != 0):
            filename = os.path.basename(response.geturl())
            filename = CourseName + "/" + filename
            #value, params = cgi.parse_header(header)
            #filename = params.get('filename')
            if(saveFile(config, response.geturl(), CourseName, overrides)):
                new_files.append(filename)
                #print "Neue Datei:", filename
        # Moodle indirekter Download
        else:
            data = response.read()
            soup = BeautifulSoup(data)
            # entweder frames oder files und dirs
            frames = soup.findAll(attrs={'src' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
            files = soup.findAll(attrs={'href' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
            dirs = soup.findAll(attrs={'href' : re.compile("subdir")})

            # PopUp Links
            popup = soup.find(attrs={'href' : re.compile("inpopup=true")})
            if(popup is not None):
                download(config, popup['href'], name, CourseName, overrides)
                #print response.info()
                #print "hu", popup['href']


            name = re.sub(u"[^a-zA-Z0-9_()äÄöÖüÜ ]", "", name).strip()
            for f in files:
                #print "Folder:", name
                if(saveFile(config, f['href'], CourseName, overrides)):
                    new_files.append(os.path.basename(f['href']))
                    #print "Neue Datei:", filename

            for d in dirs:
                # basename mal anders missbrauchen :-D
                folder = os.path.basename(d['href'])
                #print "Gehe in folder:", folder
                folder = name + "/" + folder
                href = "http://moodle.uni-duisburg-essen.de/mod/resource/" + d['href']
                download(config, href, folder, CourseName, overrides)

            # jojo eigentlich nur eine datei...
            for inli in frames:
                if(saveFile(config, inli['src'], CourseName, overrides)):
                    new_files.append(os.path.basename(inli['src']))
                    #print "Neue Datei:", filename
    return new_files

def saveFile(config, url, modul, overrides):
    # Find local filepath
    fullFileName = localfile(url, modul, overrides)

    # Update file and return if localfile was modified
    test = config.getboolean("uniload", "test")
    return File(url, fullFileName, test=test).update()

def localfile(url, modul, overrides):
    newpath = "/".join(url.split("/")[5:])
    newpath = newpath.replace("?forcedownload=1", "")
    for o in overrides.values():
        if (not 'regexp' in o or re.search(o['regexp'], newpath) is not None) and (not 'remote' in o or os.path.dirname(newpath).startswith(o['remote'])):
            if 'remote' in o:
                newpath = newpath.replace(o['remote'] + "/", "")
            return os.path.join(modul, o['folder'], newpath)
    return os.path.join(modul, "stuff", newpath)
