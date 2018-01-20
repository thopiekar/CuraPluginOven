# Copyright (c) 2018 Thomas Karl Pietrowski

import argparse

# File and OS handling
import json
import os
import shutil
import sys
from urllib.parse import urlparse

# Building the package
import compileall
import py_compile

# packaging the plugin
import zipfile

# File extensions
system_files = [".",
                "Thumbs.db"]

python_sources = [".py"]
python_bytecompiled = [".pyc",
                       ".pyo",
                       ]
python_files = python_sources + python_bytecompiled

excluded_extentions = python_bytecompiled

essential_json_fields = ("name",
                         "i18n-catalog",
                         "author",
                         "email",
                         "version",
                         "description")

def checkValidPlugin(path):
    # A plugin must be a folder
    if not os.path.isdir(path):
        return False
    print("* Verify: Found sources")

    # A plugin must contain an __init__.py
    if not os.path.isfile(os.path.join(path, "__init__.py")):
        return False
    print("* Verify: Found __init__ file")

    # .. and a plugin must contain an plugin.json!
    if not os.path.isfile(os.path.join(path, "plugin.json")):
        return False
    print("* Verify: Found plugin definition")
    plugin_json = loadPluginJSON(args.source)
    print("* Verify: Passed syntax verification of plugin definition")

    # .. and a plugin must contain an plugin.json!
    if not os.path.isfile(os.path.join(path, "LICENSE")):
        return False
    print("* Verify: Found Licence file")

    # The JSON also should contain a license definition!
    for keyword in essential_json_fields:
        if keyword not in plugin_json.keys():
            print("! ERROR: Missing keyword in plugin definition: {}".format(keyword))
            return False
        else:
            print("* Verify: Found keyword in \"{}\" definition.".format(keyword))

    print("i Verification passed!")

    return True

def prepareBuildDirectory(build_path):
    if os.path.isdir(build_path):
        if len(os.listdir(build_path)):
            print("- Warning: The given build path is neither a new location nor empty. Cleaning it up!")
            shutil.rmtree(build_path)
    os.makedirs(build_path,
                exist_ok = True)

    print("i Build directory prepared!")

def loadPluginJSON(source_path):
    json_file = open(os.path.join(source_path,
                                  "plugin.json",
                                  )
                    )
    return json.load(json_file)

def compileAllPySources(variant, optimize = -1):
    # zip_handle is zipfile handle
    for walked in os.walk(args.source):
        root = walked[0]
        filenames = walked[2]
        for filename in filenames:
            fullname = os.path.join(root, filename)
            relative_filename = os.path.relpath(fullname, args.source)
            if checkForIgnorableFiles(relative_filename):
                continue
            filename_wo_extension, extension = os.path.splitext(filename)
            if extension in python_sources:
                destdir = os.path.join(args.build,
                                       relative_filename)
                destdir = os.path.split(destdir)[0]
                os.makedirs(destdir, exist_ok = True)
                if variant in ("binary+source", "source"):
                    filename_copied = "{}/{}".format(destdir, filename)
                    shutil.copyfile(fullname,
                                    filename_copied
                                    )
                    print("* Copying: {}".format(relative_filename))
                    if variant is "binary+source":
                        compileall.compile_file(filename_copied,
                                            ddir = relative_filename,
                                            quiet = 2,
                                            optimize = optimize,
                                            )
                        print("* Compiling: {}".format(relative_filename))
                elif variant is "binary":
                    py_compile.compile(fullname,
                                       cfile = "{}/{}.{}".format(destdir, filename_wo_extension, "pyc"),
                                       doraise = True,
                                       optimize = optimize,
                                       )
                    print("* Compiling: {}".format(relative_filename))
    print("i Python files compiled and optionally copied source(s)!")

def copyOtherFiles():
    # zip_handle is zipfile handle
    for walked in os.walk(args.source):
        root = walked[0]
        filenames = walked[2]
        for filename in filenames:
            if filename.startswith("."): # dot files
                continue
            if filename in system_files: # system files
                continue
            if os.path.splitext(filename)[1] in python_files: # python files
                continue
            fullname = os.path.join(root, filename)
            relative_filename = os.path.relpath(fullname, args.source)
            if checkForIgnorableFiles(relative_filename):
                continue
            print("* Copying: {}".format(relative_filename))

            destdir = os.path.split(os.path.join(args.build,
                                                 relative_filename)
                                                 )[0]
            os.makedirs(destdir, exist_ok = True)
            shutil.copyfile(fullname,
                            os.path.join(destdir, filename)
                            )
    print("i Copied other files!")

def checkForIgnorableFiles(relative_filename):
    checked_entries = []
    for entry in relative_filename.split(os.sep):
        if entry.startswith("."): # dot files and directories
            return True
            break
        this_dir = os.path.join(args.source, *checked_entries, entry)
        if entry in ("test","tests") and os.path.isdir(this_dir): # test directories
            return True
            break
        checked_entries.append(entry)
    return False

def getFlavour(path):
    imports_cura = False
    imports_uranium = False
    for walked in os.walk(path):
        root = walked[0]
        filenames = walked[2]
        for filename in filenames:
            filename = os.path.join(root, filename)
            extension = os.path.splitext(filename)[1]
            if extension in python_sources:
                source_file = open(filename)
                for line in source_file.readlines():
                    if "import" in line and "cura." in line:
                        imports_cura = True
                    elif "import" in line and "UM." in line:
                        imports_uranium = True

    if imports_cura:
        return "cura"
    elif imports_uranium:
        return "uranium"
    else:
        raise ValueError("This is impossible! You need to import Uranium at least!")

def requiresCura(path):
    return getFlavour(path) is "cura"

def isUrlAddress(address):
    try:
        urlparse(address)
        return True
    except:
        return False

def getSource(location):
    if os.path.isdir(location):
        return location

    if isUrlAddress(location):
        if os.path.isdir(args.downloaddir):
            print("- Warning: The given download path is not a empty location. Cleaning it up!")
            shutil.rmtree(args.downloaddir)
        if location.endswith(".git"):
            ret = os.system("git clone {} --single-branch --depth 1 --recurse-submodules {} {}".format(args.gitargs, location, args.downloaddir))
            if not ret:
                return args.downloaddir

    return None

def buildPackage(metadata, compression = zipfile.ZIP_DEFLATED):
    plugin_name = metadata["i18n-catalog"]
    plugin_extension = ["umplugin", "curaplugin"][requiresCura(args.source)]
    plugin_file = "{}-{}.{}".format(plugin_name,
                                    metadata["version"],
                                    plugin_extension)
    plugin_file = os.path.join(args.destination, plugin_file)
    if os.path.isfile(plugin_file):
        os.remove(plugin_file)

    # Cura convention: Plugin inside the zip needs to be in a directory with the same name of the plugin itself.
    zip_object = zipfile.ZipFile(plugin_file, "w",
                                 compression = compression)
    for walked in os.walk(args.build):
        root = walked[0]
        files = walked[2]
        for file in files:
            filename = os.path.relpath(os.path.join(root, file), args.build)
            print("* Packaging: {}".format(filename))
            zip_object.write(os.path.join(args.build, filename),
                             os.path.join(plugin_name, filename)
                             )
    print("i Package built: {}".format(plugin_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", "--src", "-s",
                        dest="source",
                        type = str,
                        default = "source",
                        help = "Location of the source folder")
    parser.add_argument("--downloaddir", "--dldir", "-dd",
                        dest="downloaddir",
                        type = str,
                        default = "download",
                        help = "Location of the download folder")
    parser.add_argument("--build", "--bld", "-b",
                        dest="build",
                        type = str,
                        default = "build",
                        help = "Location of the build folder")
    parser.add_argument("--destination", "--dest", "-d",
                        dest="destination",
                        type = str,
                        default = os.curdir,
                        help = "Location, where to place the resulting package")
    parser.add_argument("--variant", "--var", "-v",
                        dest="variant",
                        type = str,
                        default = "binary+source",
                        choices = ["binary+source",
                                   "binary",
                                   "source",
                                   ],
                        help = "Variant of build")
    parser.add_argument("--compression", "--comp", "-c",
                        dest="compression",
                        type = str,
                        default = "lzma",
                        choices = ["none",
                                   "zlib",
                                   "bzip2",
                                   "lzma",
                                   ],
                        help = "Package compression")
    parser.add_argument("--optimize", "--opt", "-o",
                        dest="optimize",
                        type = int,
                        default = 2,
                        choices = range(3),
                        help = "Location of the build folder")
    parser.add_argument("--gitargs", "-ga",
                        dest="gitargs",
                        type = str,
                        default = "",
                        help = "git arguments")
    args = parser.parse_args()

    # Getting the real paths
    args.source = getSource(args.source)
    args.source = os.path.realpath(args.source)
    args.build = os.path.realpath(args.build)

    # Source validation check
    if not checkValidPlugin(args.source):
        print("--> The provided source can not be built!")
        sys.exit(1)

    # Preparing the compression option
    if args.compression is "none":
        args.compression = zipfile.ZIP_STORED
    elif args.compression is "zlib":
        args.compression = zipfile.ZIP_DEFLATED
    elif args.compression is "bzip2":
        args.compression = zipfile.ZIP_BZIP2
    elif args.compression is "lzma":
        args.compression = zipfile.ZIP_LZMA
    else:
        print("Unknown compression format!")
        sys.exit(1)

    # Reading the JSON file and checking which flavour of package needs to be built
    plugin_json = loadPluginJSON(args.source)
    requiresCura(args.source)

    # Preparing build..
    prepareBuildDirectory(args.build)
    # Build all files.. Compile and copy them..
    compileAllPySources(args.variant, optimize = args.optimize)
    copyOtherFiles()
    # Building the package
    buildPackage(plugin_json, compression=zipfile.ZIP_DEFLATED)