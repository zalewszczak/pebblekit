#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import zipfile
import argparse
import json
import time
import stm32_crc
import socket
import pprint

MANIFEST_VERSION = 1
BUNDLE_PREFIX = 'bundle'

class MissingFileException(Exception):
    def __init__(self, filename):
        self.filename = filename

def flen(path):
    statinfo = os.stat(path)
    return statinfo.st_size

def stm32crc(path):
    with open(path, 'r+b') as f:
        binfile = f.read()
        return stm32_crc.crc32(binfile) & 0xFFFFFFFF

def check_paths(*args):
    for path in args:
        if not os.path.exists(path):
            pprint.pprint(path)
            raise MissingFileException(path)

class PebbleBundle(object):
    def __init__(self):
        self.generated_at = int(time.time())
        self.bundle_manifest = {
            'manifestVersion' : MANIFEST_VERSION,
            'generatedAt' : self.generated_at,
            'generatedBy' : socket.gethostname(),
            'debug' : {},
            }
        self.bundle_files = []
        self.has_firmware = False
        self.has_watchapp = False
        self.has_resources = False

    def add_firmware(self, firmware_path, firmware_type, firmware_timestamp, firmware_hwrev):
        if self.has_firmware:
            raise Exception("Added multiple firmwares to a single bundle")

        if self.has_watchapp:
            raise Exception("Cannot add firmware and watchapp to a single bundle")

        if firmware_type != 'normal' and firmware_type != 'recovery':
            raise Exception("Invalid firmware type!")

        check_paths(firmware_path)
        self.type = 'firmware'
        self.bundle_files.append(firmware_path)
        self.bundle_manifest['firmware'] = {
            'name' : os.path.basename(firmware_path),
            'type' : firmware_type,
            'timestamp' : firmware_timestamp,
            'hwrev' : firmware_hwrev,
            'size' : flen(firmware_path),
            'crc' : stm32crc(firmware_path),
            }
        self.has_firmware = True
        return True

    def add_resources(self, resource_path, resource_map_path, resources_timestamp):
        if self.has_resources:
            raise Exception("Added multiple resource packs to a single bundle")

        check_paths(resource_path, resource_map_path)
        self.bundle_files.append(resource_path)

        with open(resource_map_path) as fm:
            resource_map = json.load(fm)

        self.bundle_manifest['resources'] = {
            'name' : os.path.basename(resource_path),
            'friendlyVersion' : resource_map['friendlyVersion'],
            'timestamp' : resources_timestamp,
            'size' : flen(resource_path),
            'crc' : stm32crc(resource_path),
            }
        self.bundle_manifest['debug']['resourceMap'] = resource_map

        self.has_resources = True
        return True

    def add_watchapp(self, watchapp_path, app_timestamp, app_req_fw_version):
        if self.has_watchapp:
            raise Exception("Added multiple apps to a single bundle")

        if self.has_firmware:
            raise Exception("Cannot add watchapp and firmware to a single bundle")
        
        check_paths(watchapp_path)
        self.type = 'application'
        self.bundle_files.append(watchapp_path)
        self.bundle_manifest['application'] = {
            'name' : os.path.basename(watchapp_path),
            'timestamp': app_timestamp,
            'reqFwVer': app_req_fw_version,
            'size': flen(watchapp_path),
            'crc': stm32crc(watchapp_path)
            }
        self.has_watchapp = True
        return True

    def write(self, out_path = None, verbose = False):
        if not (self.has_firmware or self.has_watchapp):
            raise Exception("Bundle must contain either a firmware or watchapp")

        self.bundle_manifest['type'] = self.type

        if not out_path:
            out_path = 'pebble-{}-{:d}.pbz'.format(self.type, self.generated_at)

        if verbose:
            pprint.pprint(self.bundle_manifest)
            print('writing bundle to {}'.format(out_path))

        with zipfile.ZipFile(out_path, 'w') as z:
            for f in self.bundle_files:
                z.write(f, os.path.basename(f))
            z.writestr('manifest.json', json.dumps(self.bundle_manifest))

        if verbose:
            print('done!')

def check_required_args(opts, *args):
    options = vars(opts)
    for required_arg in args:
        try:
            if not options[required_arg]:
                raise Exception("Missing argument {}".format(required_arg))
        except KeyError:
            raise Exception("Missing argument {}".format(required_arg))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a firmware+resources bundle for a Pebble.')
    parser.add_argument('--firmware', help='path to the firmware .bin')
    parser.add_argument('--firmware-timestamp', help='the (git) timestamp of the firmware', type=int)
    parser.add_argument('--watchapp', help='path to the watchapp .bin')
    parser.add_argument('--watchapp-timestamp', help='the (git) timestamp of the app', type=int)
    parser.add_argument('--req-fw', help='the required firmware to run the app', type=int)
    parser.add_argument('--board', help='the board for which the firmware was built', choices = ['bigboard', 'ev1', 'ev2'])
    parser.add_argument('--firmware-type', help='the type of firmware included in the bundle', choices = ['normal', 'recovery'])
    parser.add_argument('--resources', help='path to the generated resource pack')
    parser.add_argument('--resource-map', help='path to the resource map')
    parser.add_argument('--resources-timestamp', help='the (git) timestamp of the resource pack', type=int)
    parser.add_argument("-v", "--verbose", help="print additional output", action="store_true")
    parser.add_argument("-o", "--outfile", help="path to the output file")
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    b = PebbleBundle()

    if args.watchapp:
        check_required_args(args, 'watchapp_timestamp', 'req_fw')
        watchapp_path = os.path.expanduser(args.watchapp)
        b.add_watchapp(watchapp_path, args.watchapp_timestamp, args.req_fw)

    if args.firmware:
        check_required_args(args, 'firmware_timestamp', 'board', 'firmware_type')
        firmware_path = os.path.expanduser(args.firmware)
        b.add_firmware(firmware_path, args.firmware_type, args.firmware_timestamp, args.board)

    if args.resources:
        check_required_args(args, 'resource_map', 'resources_timestamp')
        resource_path = os.path.expanduser(args.resources)
        resmap_path = os.path.expanduser(args.resource_map)
        b.add_resources(resource_path, resmap_path, args.resources_timestamp)

    b.write(args.outfile, args.verbose)
