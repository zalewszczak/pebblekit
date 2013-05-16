if [ $# -eq 0 ] || [ "$1" == "-h" ]; then
  echo "$(basename "$0") [-h] [pebble-apps-loc, sdk-loc] [-clean]

  This script will build pebble watches, demos and templates
  where:
      -h  show this help text
      pebble-apps-loc   the full path to the '/<path>/pebble-apps' folder
      sdk-loc           the full path to the '/<path>/sdk' folder
      -clean            remove the symlinks that are created"
  exit
fi

# NOTE: in both functions:
#   $1 is the path to the .../pebble-apps folder
#   $2 is the name of the subfolder within pebble-apps to build
#   $3 is the path to the .../sdk folder

build_sdk () {
  for i in $1/$2/* ; do
    if [ -d "$i" ]; then
      if [ -d "$i/src" ]; then
        ./tools/create_pebble_project.py --symlink-only $3/sdk/ $i
        cd $i
        ./waf configure #> /dev/null
        ./waf build #> /dev/null
        cd $1
      fi
    fi
  done
}

clean_sdk_symlinks () {
  for i in $1/$2/* ; do
    if [ -d "$i" ]; then
      echo $i
      if [ -d "$i/src" ]; then
        cd $i
        echo "cleaning " $i
        rm include
        rm lib
        rm pebble_app.ld
        rm tools
        rm waf
        rm wscript
        cd resources
        rm wscript
        cd $1
      fi
    fi
  done
}

if [ "$3" == "-clean" ]; then
  # user wants to clean up symlinks
  echo "CLEANING UP SYMLINKS"
  clean_sdk_symlinks $1 "watches" $2
  clean_sdk_symlinks $1 "demos" $2
  clean_sdk_symlinks $1 "templates" $2
else
  echo "BUILDING SDK"
  build_sdk $1 "watches" $2
  build_sdk $1 "demos" $2
  build_sdk $1 "templates" $2
fi
