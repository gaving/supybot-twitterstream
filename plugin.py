###
# Copyright (c) 2011, Gavin Gilmour
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import decimal
import locale
import telnetlib
import threading
import time
import re
import json
import datetime
import socket

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import twitter
import tweetstream

class TwitterStream(callbacks.Plugin):
    """Add the help for "@plugin help TwitterStream" here
    This should describe *how* to use this plugin."""
    threaded = True
    callAfter = ['Services']

    def __init__(self, irc):
        self.__parent = super(TwitterStream, self)
        self.__parent.__init__(irc)
        self.e = threading.Event()
        self.started = threading.Event()

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        if not self.started.isSet() and self.registryValue('autostart'):
            self._start(irc)

    def _monitor(self, irc):
        while not self.e.isSet():
            try:
                # tweetstream bug where it waits for minimum data before sending
                print self.registryValue('following')
                api = twitter.Api()
                following = [ api.GetUser(x).id for x in self.registryValue('following') ]
                with tweetstream.FilterStream(self.registryValue('account.username'), self.registryValue('account.password'), follow=following) as stream:
                    for tweet in stream:
                        irc.reply("%s: %s" % (tweet["user"]["screen_name"], tweet["text"]))
            except tweetstream.ConnectionError, e:
                self.log.error('TweetStream error: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                continue # keep going no matter what
            except Exception, e:
                self.log.error('Error in TwitterStream: %s: %s' % \
                            (e.__class__.__name__, str(e)))

        self.started.clear()

    def _start(self, irc):
        if not self.registryValue('following'):
            irc.error("Nobody to follow")

        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            # old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(None) # supybot sets a global timeout elsewhere :/
            socket._fileobject.default_bufsize = 0 # http://blog.persistent.info/2009/08/twitter-streaming-api-from-python.html
            t = threading.Thread(target=self._monitor, name='TwitterStream', kwargs={'irc':irc})
            t.start()
            if hasattr(irc, 'reply'):
                irc.reply("Monitoring start successful. Now monitoring twitter data.")
            else:
                if hasattr(irc, 'error'):
                    irc.error("Error connecting to server. See log for details.")
        else:
            irc.error("Monitoring already started.")

    def start(self, irc, msg, args):
        """takes no arguments

        Starts monitoring twitter data
        """
        irc.reply("Starting twitter monitoring.")
        self._start(irc)
    start = wrap(start, ['owner'])

    def stop(self, irc, msg, args):
        """takes no arguments

        Stops monitoring twitter data
        """
        irc.reply("Stopping twitter monitoring.")
        self.e.set()
    stop = wrap(stop, ['owner'])

    def die(self):
        self.e.set()
        self.__parent.die()


Class = TwitterStream


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
