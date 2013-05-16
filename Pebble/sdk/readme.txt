Pebble SDK

##################
How to Build:
##################

From this directory:

$ ./waf configure
$ ./waf build

This will build all C files in the src/ directory.


##################
How to install:
##################

You need to serve the `.pbw` file generated in the `build` directory over HTTP so your phone can download it.

The easiest way (on Android or with iOS Pebble App 1.0.5+) is to use:

    pushd build/ && python -m SimpleHTTPServer 8000

Then visit the IP address of your computer from your phone's internet browser:

    e.g. http://<address>:8000/

Click on the file named `app_<number>.pbw` in the list and the Pebble App will install it to your watch.

(Alternatively you can consider using a tool from the `libpebble` project.)


##################
Size Limits:
##################

Currently, app binaries should be no larger than 24KB and app resources no larger than 96KB.

These limits are currently statically defined, but may be changed or made more dynamic in the future.
