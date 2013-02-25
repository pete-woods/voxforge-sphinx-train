# Copyright (C) 2005-2012 Canonical Ltd
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''
hudkeywords.cli -- shortdesc

hudkeywords.cli is a description

It defines classes_and_methods

'''

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

import train

__all__ = []
__version__ = 1.0

class CLIError(BaseException):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "Error: %s" % msg

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_version_message = '%%(prog)s %s' % (program_version)
    program_shortdesc = 'Simple python tool for creating po and keyword XML files for HUD.'

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("command", help="Command to run")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level")
        parser.add_argument("-d", "--dir", dest="dir", help="Directory", default=os.getcwd())
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        
        # Process arguments
        args = parser.parse_args()
        
        if args.verbose > 0:
            print("Making new training folder at [{}]".format(args.dir))
        t = train.Train(args.dir)
        
        if args.verbose > 0:
            print("Running command [{}]".format(args.command))
        
        if args.command == "all":
            t.clean()
            t.convert_flac()
            t.link_mfc()
            t.transcript()
            t.build_lm()
            t.templates()
            t.setup()
        elif args.command == "download":
            t.download()
        elif args.command == "unpack":
            t.unpack()
        elif args.command == "convert_flac":
            t.convert_flac()
        elif args.command == "link_mfc":
            t.link_mfc()
        elif args.command == "transcript":
            t.transcript()
        elif args.command == "build_lm":
            t.build_lm()
        elif args.command == "templates":
            t.templates()
        elif args.command == "setup":
            t.setup()
        elif args.command == "run":
            t.run()
        elif args.command == "clean":
            t.clean()
        else:
            raise CLIError("Command [{}] unknown.".format(args.command))
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except CLIError, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + e.msg + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2
#    except Exception, e:
#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + repr(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help\n")
#        return 2
