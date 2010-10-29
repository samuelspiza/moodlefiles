# -*- coding: utf-8 -*-
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>
#
"""fileupdater - a package for downloading and updating files"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__version__ = "0.1.1"
__all__ = ["File","Filegroup","absUrl","absFindall","getResponse",
           "safe_getResponse"]

import re
import os
import urllib
import urllib2

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

HEADER = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
          'Accept-Language': 'de',
          'Accept-Encoding': 'utf-8'}

class ArgumentError(Exception):
    pass

def absUrl(site, href):
    """Returns an absolute URL.
    
    It takes the a site and a path (e.g. argument to an 'href' or 'src'
    parameter of a HTML tag). The absolute URL will be composed in the same way
    a web browser does.
    """
    href = href.replace("\\", "/")
    if href.startswith("http://") or href.startswith("https://"):
        return href
    comps = href.split("/")
    if href[:1] == "/":
        comps[0:1] = site.split("/")[:3]
    else:
        comps[0:0] = site.split("/")[:-1]
    i = 2
    while i < len(comps):
        if comps[i] == '.':
            del comps[i]
        elif comps[i] == '..':
            if i > 0 and comps[i-1] != '..':
                del comps[i-1:i+1]
                i -= 1
            else:
                i += 1
        else:
            i += 1
    return "/".join(comps)

def absFindall(url, regexp=None, regobj=None, content=None):
    """Returns a list of absolute URLs of all found paths matching a given
    regular expression in the content of a web site.
    
    The regular expression can be passed as a string (regexp) or as a
    precompiled regexObject (regobj). Either 'regexp' or 'regobj' must not be
    'None'. If both are not 'None', 'regexp' will be used.
    
    If the content of the page (url) was retrieved before this function is
    called, it can be passed as 'content' to minimize HTTP-requests.
    """
    if content is None:
        content = safe_getResponse(url).read()
    if regexp is not None:
        return [absUrl(url, m) for m in re.findall(regexp, content)]
    elif regobj is not None:
        return [absUrl(url, m) for m in regobj.findall(content)]
    else:
        raise ArgumentError, "'regexp' and 'regobj' are both None."

def getResponse(url, postData=None):
    """Opens an URL with POST data.
    
    The POST data must be a dictionary.
    """
    if(postData is not None):
        postData = urllib.urlencode(postData)
    req = urllib2.Request(url, postData, HEADER)
    return urllib2.urlopen(req)

def safe_getResponse(url, postData=None):
    """Opens an URL with POST data and catches errors.
    
    Returns None if an error occurs. Catches urllib2.HTTPError, ValueError and
    urllib2.URLError.
    """
    try:
        return getResponse(url, postData=postData)
    except urllib2.HTTPError, e:
        print "Error Code: %s" % e.code
    except ValueError, e:
        print e
    except urllib2.URLError, e:
        print "Reason: %s" % e.reason
    return None

class File:
    """Represents a file by connecting a local path and an remote URL.
    
    Can be used to check if the local file is synched to the remote one.
    Provides methods for updating the local file to the remote one if
    nesseccary or forcing a download.
    """

    def __init__(self, remote, local, response=None, text=False, test=True):
        self.name = os.path.basename(local)
        self.remote = remote
        self.local = local
        self.text = text
        self.test = test
        self.clean()

    def clean(self):
        self.response = None
        self.oldlen = None
        self.newlen = None
        self.newcontent = None
        self.isnew = None
        self.haschanged = None

    def update(self):
        if self.check():
            return self.download()
        return False

    def check(self):
        return self.isNew() or self.hasChanged()

    def isNew(self):
        if self.isnew is None:
            self.isnew = not os.path.exists(self.local)
        return self.isnew

    def hasChanged(self):
        if self.haschanged is None:
            if self.isNew():
                self.haschanged = False
            else:
                newlen = self.getNewLen()
                self.haschanged = newlen is not None and \
                                  self.getOldLen() != newlen
        return self.haschanged

    def getOldLen(self):
        if self.oldlen is None:
            self.oldlen = int(os.stat(self.local).st_size)
        return self.oldlen

    def getNewLen(self):
        if self.newlen is None:
            response = self.getResponse()
            if response is None:
                return None
            elif response.info().get("Content-Length") is None:
                self.newlen = len(self.getNewContent())
            else:
                self.newlen = int(response.info().get("Content-Length"))
        return self.newlen

    def getNewContent(self):
        if self.newcontent is None and self.getResponse() is not None:
            self.newcontent = self.response.read()
        return self.newcontent

    def getResponse(self):
        if self.response is None:
            self.response = safe_getResponse(self.remote)
        return self.response

    def download(self):
        newcontent = self.getNewContent()
        if newcontent is not None:
            localdir = os.path.dirname(self.local)
            if not os.path.exists(localdir):
                print "makedirs: " + localdir
                if not self.test:
                    os.makedirs(localdir)
            print "write: " + self.local
            if not self.test:
                try:
                    if self.text:
                        file = open(self.local, "w")
                    else:
                        file = open(self.local, "wb")
                    file.write(newcontent)
                    file.close()
                    return True
                except IOError, e:
                    print "IOError: " + e + ", " + self.local
        return False

    def __str__(self):
        return self.name

class Filegroup:
    def __init__(self, remote, local, start=1, text=False, test=False):
        self.remote = remote
        self.local = local
        self.start = start
        self.text = text
        self.test = test
        self.iterator = Filegroupiter(self)

    def update(self):
        for f in self.iterator:
            f.update()
        return len(self.iterator)

    def download(self):
        for f in self.iterator:
            f.download()
        return len(self.iterator)

    def getFileById(self, i):
        return self.remote.format(i), self.local.format(i)

class Filegroupiter:
    def __init__(self, group):
        self.group = group
        self.i = self.group.start
        self.errors = 0
        self.files = []

    def __iter__(self):
        return self

    def next(self):
        while self.errors < 2:
            remote, local = self.group.getFileById(self.i)
            try:
                res = getResponse(remote)
                self.i, self.errors = self.i + 1, 0
                f = File(remote, local, response=res, text=self.group.text, 
                         test=self.group.test)
                self.files.append(f)
                return f
            except urllib2.HTTPError:
                self.i, self.errors = self.i + 1, self.errors + 1
        self.group.iterator = self.files
        raise StopIteration

    def __len__(self):
        return self.i - 3
