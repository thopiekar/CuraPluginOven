# Copyright (c) 2019 Thomas Karl Pietrowski

import atexit
import argparse

# File and OS handling
import json
import os
import shutil
import sys
from urllib.parse import urlparse
from stat import ST_MODE

# Building the package
import compileall
#import py_compile

# packaging the plugin
import zipfile

# File extensions
system_files = [".",
                "Thumbs.db"]

python_sources = [".py"]
python_bytecompiled = [".pyc",
                       ".pyo",
                       ]
qml_bytecompiled = [".qmlc",
                    ]
python_files = python_sources + python_bytecompiled

excluded_extentions = [".chm", # Windows Compressed HTML Help
                       ] + python_bytecompiled + qml_bytecompiled

essential_package_fields = (("package_id",),
                            ("package_type",),
                            ("display_name",),
                            ("description",),
                            ("package_version",),
                            ("sdk_version",),
                            ("website",),
                            ("author",),
                            ("author", "author_id"),
                            ("author", "display_name"),
                            ("author", "email"),
                            ("author", "website"),
                            ("tags",),
                            )
package_600_fields = essential_package_fields + (("sdk_version_semver",),
                                                 )

essential_plugin_fields = ("name",
                           "id",
                           "i18n-catalog",
                           "author",
                           "email",
                           "version",
                           "description",
                           )

package_metadata_filename = "package.json"
plugin_metadata_filename = "plugin.json"
metadata_filenames = (package_metadata_filename,
                      plugin_metadata_filename)

license_filenames = ("LICENSE",
                     "LICENSE.txt",)
# all in lowercase
test_directories = ("test",
                    "tests",
                    )

def isUrlAddress(address):
    try:
        urlparse(address)
        return True
    except:
        return False

def removeDownload():
    shutil.rmtree(args.downloaddir)

def getSource(location):
    if os.path.isdir(location):
        return location

    if isUrlAddress(location):
        if os.path.isdir(args.downloaddir):
            print("- Warning: The given download path is not a empty location. Cleaning it up!")
            removeDownload()
        if location.endswith(".git"):
            ret = os.system("git clone {} --single-branch --depth 1 --recurse-submodules {} {}".format(args.gitargs, location, args.downloaddir))
            if not ret:
                atexit.register(removeDownload)
                return args.downloaddir

    return None

class CreatorCommon():
    default_result_extension = ""
    target_sdk = None

    def __init__(self, args):
        self.__args = args

        # Getting the real paths
        self.source_dir = os.path.realpath(args.source)
        self.build_dir = os.path.realpath(args.build)
        self.result_dir = args.destination
        self._result_name = args.result
        self.result_extension = None

        compressions = {"none": zipfile.ZIP_STORED,
                        "zlib": zipfile.ZIP_DEFLATED,
                        "bzip2": zipfile.ZIP_BZIP2,
                        "lzma": zipfile.ZIP_LZMA,}
        if args.compression not in compressions.keys():
            print("Unknown compression format!")
        else:
            self.compression = compressions[args.compression]
        self.variant = args.variant

    @property
    def result_name(self):
        raise ValueError("result_name not implemented!")

    def verify(self):
        # Test, whether we can determine the plugin's file extension
        try:
            self.result_name
        except Exception:
            print("E Raised error, when trying to call self.result_name")
            return False

        return True

    def prepare(self):
        raise ValueError("prepare not implemented!")

    def build(self):
        raise ValueError("build not implemented!")

    def bundle(self):
        raise ValueError("bundle not implemented!")

    def test(self):
        raise ValueError("test not implemented!")

    def clean(self):
        raise ValueError("clean not implemented!")

    def loadJsonFile(self, location):
        json_file = open(location)
        result = json.load(json_file)
        json_file.close()
        return result

    def isPackageMeta(self, location = None):
        if not location:
            location = os.path.join(self.source_dir)
        if os.path.isdir(location):
            location = os.path.join(location, package_metadata_filename)
        return os.path.isfile(location)

    def loadPackageMeta(self, location = None):
        if not location:
            location = os.path.join(self.source_dir)
        if os.path.isdir(location):
            location = os.path.join(location, package_metadata_filename)
        self.package_meta = self.loadJsonFile(location)
        return self.package_meta

    def isPluginMeta(self, location = None):
        if not location:
            location = os.path.join(self.source_dir)
        if os.path.isdir(location):
            location = os.path.join(location, plugin_metadata_filename)
        return os.path.isfile(location)

    def loadPluginMeta(self, location = None):
        if not location:
            location = os.path.join(self.source_dir)
        if os.path.isdir(location):
            location = os.path.join(location, plugin_metadata_filename)
        self.plugin_meta = self.loadJsonFile(location)
        return self.plugin_meta

    def findLicenseFile(self, directory):
        result = None
        license_locations = [self.package_location, self.plugin_location]
        if directory not in license_locations:
            license_locations.append(directory)
        for license_location in license_locations:
            for license_filename in license_filenames:
                license_filepath = os.path.join(license_location, license_filename)
                if os.path.isfile(license_filepath):
                    result = license_filepath
                    break
            if result:
                break
        if not result:
            print("e LICENSE file not found!")
            return False

        self.license_file = result
        print("d Verify: LICENSE file found at: {}".format(result))
        return True

    def cleanUpBuildDirectory(self, build_path):
        if os.path.isdir(build_path):
            shutil.rmtree(build_path)
        print("i Build directory removed!")

    def prepareBuildDirectory(self, build_path, cleanup_before_creation = True):
        if cleanup_before_creation:
            self.cleanUpBuildDirectory(build_path)

        os.makedirs(build_path,
                    exist_ok = True)

        print("i Build directory prepared!")

    def checkForIgnorableFiles(self, base_path, relative_filename):
        print("d Checking whether file can be ignored: {}".format(relative_filename))
        checked_entries = []
        for entry in relative_filename.split(os.sep):
            # TODO: Implement args.exclude here
            if entry.startswith("."): # dot files and directories
                return True
            this_path = os.path.join(base_path, *checked_entries, entry)
            if this_path == os.path.split(__file__)[0]: # Filtering out CPO itself
                return True
            if this_path.startswith(self.build_dir): # Ignore the build dir inside source dir
                return True
            if entry.lower() in test_directories and os.path.isdir(this_path): # test directories
                return True
            if os.path.isfile(this_path):
                for extension in excluded_extentions:
                    if entry.endswith(extension):
                        return True
            checked_entries.append(entry)
        return False

    def compileAllPySources(self, source, build, variant, optimize = -1):
        # zip_handle is zipfile handle
        for root, dirs, filenames in os.walk(source):
            for filename in filenames:
                fullname = os.path.join(root, filename)
                relative_filename = os.path.relpath(fullname, source)
                if self.checkForIgnorableFiles(source, relative_filename):
                    continue
                _, extension = os.path.splitext(filename)
                if extension in python_sources:
                    destdir = os.path.join(build,
                                           relative_filename)
                    destdir = os.path.split(destdir)[0]
                    os.makedirs(destdir, exist_ok = True)
                    if variant in ("binary+source", "source", "binary"):
                        filename_copied = "{}/{}".format(destdir, filename)
                        shutil.copyfile(fullname,
                                        filename_copied
                                        )
                        os.chmod(filename_copied, 0o600)
                        print("d Copying: {}".format(relative_filename))
                        if variant in ("binary+source", "binary"):
                            compileall.compile_file(filename_copied,
                                                ddir = relative_filename,
                                                quiet = 2,
                                                optimize = optimize,
                                                )
                            print("d Compiled: {}".format(relative_filename))
                        if variant is "binary":
                            if relative_filename != "__init__.py":
                                print("d Removing: {}".format(relative_filename))
                                os.remove(filename_copied)
                    else:
                        print("e Invalid variant!")
        print("i Python files compiled and optionally copied source(s)!")

    def copyOtherFiles(self, source, build, ignore_dot_files = True):
        # zip_handle is zipfile handle
        for root, dirs, filenames in os.walk(source):
            for filename in filenames:
                if filename.startswith(".") and ignore_dot_files: # dot files
                    continue
                if filename in system_files: # system files
                    continue
                if filename in license_filenames: # license files
                    continue
                if filename in metadata_filenames: # metadata files
                    continue
                if os.path.splitext(filename)[1] in python_files: # python files
                    continue
                fullname = os.path.join(root, filename)
                relative_filename = os.path.relpath(fullname, source)
                if self.checkForIgnorableFiles(source, relative_filename):
                    continue
                print("d Copying: {}".format(relative_filename))

                destdir = os.path.split(os.path.join(build,
                                                     relative_filename,
                                                     )
                                        )[0]
                os.makedirs(destdir, exist_ok = True)
                filename_copied = os.path.join(destdir, filename)
                shutil.copyfile(fullname,
                                filename_copied
                                )
                os.chmod(filename_copied, 0o600)
        print("i Copied other files!")

    def buildPluginMetadata(self, location = None, sort_keywords = False, api = None):
        if not location:
            location = self.build_dir
        if os.path.isdir(location):
            location = os.path.join(location, plugin_metadata_filename)

        metadata = self.plugin_meta.copy()
        if api:
            metadata["api"] = self.target_api

        # Filtering out some custom keywords
        if "minimum_api" in metadata.keys():
            del metadata["minimum_api"]

        with open(location, "w") as metadata_file:
            metadata_file.write(json.dumps(metadata,
                                           sort_keys = sort_keywords,
                                           indent = 4,
                                           )
            )

    def buildPackageMetadata(self, location = None, sort_keywords = False):
        if not location:
            location = self.build_dir
        if os.path.isdir(location):
            location = os.path.join(location, package_metadata_filename)
        metadata = self.package_meta.copy()

        if self.target_sdk:
            if type(self.target_sdk) in (tuple, list):
                metadata["sdk_version"] = ".".join([str(x) for x in self.target_sdk])
            elif type(self.target_sdk) is int:
                metadata["sdk_version"] = self.target_sdk
            else:
                raise ValueError("Wrong data type of target_sdk!")

        # Filtering out some old keywords
        if type(metadata["sdk_version"]) is int:
            sdk_major = metadata["sdk_version"]
        else:
            sdk_major = metadata["sdk_version"][0]
        if "tags" in metadata.keys() and sdk_major >= 6:
            del metadata["tags"]

        with open(location, "w") as metadata_file:
            metadata_file.write(json.dumps(metadata,
                                           sort_keys = sort_keywords,
                                           indent = 4,
                                           )
            )

class PackageCreator(CreatorCommon):
    "Creates package files based on package info (package.json)"

    target_sdk = 0
    default_result_extension = "curapackage"

    CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default ContentType="application/vnd.openxmlformats-package.relationships+xml" Extension="rels" />
  <Default ContentType="application/x-ultimaker-material-profile" Extension="xml.fdm_material" />
  <Default ContentType="application/x-ultimaker-material-sig" Extension="xml.fdm_material.sig" />
  <Default ContentType="application/x-ultimaker-quality-profile" Extension="inst.cfg" />
  <Default ContentType="application/x-ultimaker-machine-definition" Extension="def.json" />
  <Default ContentType="text/json" Extension="json" />
</Types>
"""

    RELATION_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rel0" Target="/package.json" Type="http://schemas.ultimaker.org/package/2018/relationships/opc_metadata" />
</Relationships>
"""

    RELATION_PLUGIN_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rel0" Target="/files/plugins" Type="plugin" />
</Relationships>
"""

    def __init__(self, args):
        super().__init__(args)
        self.package_location = self.source_dir
        self.plugin_location = None

        # Load package metadata
        self.loadPackageMeta()

    def verify(self):
        super().verify()

        # Source validation check
        if not self.checkValidSource():
            print("e The provided source is not valid!")
            return False

        if not self.verifyPluginMetadata():
            print("e The provided source is not valid!")
            return False

        if not super().verify():
            return False

        return True

    def checkValidSource(self, directory = None):
        if not directory:
            directory = self.source_dir

        # A plugin must be a folder
        if not os.path.isdir(directory):
            return False
        print("d Verify: Found project base")

        # Checking whether all keywords are present
        for keywords in package_600_fields:
            test_object = self.package_meta
            for keyword in keywords:
                if keyword not in test_object.keys():
                    print("! ERROR: Missing keyword in metadata: {}".format(repr(".".join(keywords))))
                    return False
                else:
                    test_object = test_object[keyword]
            print("d Verify: Found keyword in metadata: {}".format(repr(".".join(keywords))))

        # Trying to find source base
        expected_plugin_locations = (os.path.join(self.source_dir, self.package_meta["package_type"], self.package_meta["package_id"]), # As placed in the final package
                                 os.path.join(self.source_dir, self.package_meta["package_id"]), # as done at CuraDrive
                                 os.path.join(self.source_dir, ), # in case the package.json is in the same directory as the sources
                                 )
        result = False
        for expected_plugin_location in expected_plugin_locations:
            print("d Testing path: {}".format(repr(expected_plugin_location)))
            # Checking for some general requirements here:
            # A source base must contain an __init__.py
            if not os.path.isfile(os.path.join(expected_plugin_location, "__init__.py")):
                continue
            print("d Verify: Found __init__ file")

            print("i Found source base")
            self.plugin_location = expected_plugin_location
            result = True
            break

        if not result:
            print("e Plugin sources not found!")
            return False

        if not self.findLicenseFile(directory):
            print("e License not found!")
            return False

        # Plugin data
        self.loadPluginMeta(self.plugin_location)
        self.checkValidPluginMetadata()

        # All checks done
        print("i Verification passed!")
        return True

    def checkValidPluginMetadata(self):
        # Checking whether target SDK version is within the list of supported SDKs
        if type(self.target_sdk) in (tuple, list):
            if not ".".join([str(enum) for enum in self.target_sdk]) in self.plugin_meta["supported_sdk_versions"]:
                return False
        elif type(self.target_sdk) is int:
            if "minimum_api" in self.plugin_meta.keys():
                minimum_api = self.plugin_meta["minimum_api"]
            else:
                minimum_api = self.plugin_meta["api"]
            plugin_api_range = range(minimum_api, self.plugin_meta["api"] + 1)
            if not self.target_sdk in plugin_api_range:
                return False
        else:
            print("e Wrong datatype for target_sdk!")
            return False

        return True

    def verifyPluginMetadata(self):
        if not self.plugin_meta or not self.package_meta:
            raise ValueError("One of the metadata or both is None and/or empty!")

        # Equality of IDs
        if not self.plugin_meta["id"] == self.package_meta["package_id"]:
            print("e Plugin ID is not the same as package ID!")
            return False
        # Equality of the names
        if not self.plugin_meta["name"] == self.package_meta["display_name"]:
            print("e Plugin name is not the same as display name!")
            return False
        # Equality of the names
        if not self.plugin_meta["version"] == self.package_meta["package_version"]:
            print("e Plugin version is not the same as package version")
            return False
        if not self.package_meta["sdk_version"] == int(self.package_meta["sdk_version_semver"].split(".")[0]):
            print("e SDK version is not the same as SDK version semver[0]!")
            return False
        if not self.package_meta["package_type"] == "plugin":
            print("Unexpected package format: {}".format(repr(self.package_meta["package_type"])))
            return False
        return True

    def prepare(self):
        # Preparing build..
        self.prepareBuildDirectory(self.build_dir)

    def build(self):
        # Build all files.. Compile and copy them..
        _build_base = os.path.join(self.build_dir, "files", "plugins", self.package_meta["package_id"])
        self.compileAllPySources(self.plugin_location, _build_base, self.variant, optimize = args.optimize)
        self.copyOtherFiles(self.plugin_location, _build_base)
        shutil.copy(self.license_file, _build_base)
        self.buildPackageMetadata(sort_keywords = True)
        self.buildPluginMetadata(location = _build_base)

    def bundle(self):
        # Building the package
        self.buildPackageFile(self.build_dir)

    def test(self):
        pass

    def clean(self):
        # Clean up build directory
        self.cleanUpBuildDirectory(self.build_dir)

    def generatePluginMetadata(self, override = False):
        if os.path.isfile(os.path.join(self.plugin_location, plugin_metadata_filename)) and not override:
            print("w Metadata of the plugin already exists. Skipping automated creation!")
            return

    @property
    def result_name(self):
        if self._result_name:
            return self._result_name

        if self.result_extension:
            result_extension = self.result_extension
        else:
            result_extension = self.default_result_extension

        if type(self.target_sdk) in (tuple, list):
            sdk_tag = "sdk-" + "".join([str(x) for x in self.target_sdk])
        elif type(self.target_sdk) is int:
            sdk_tag = "sdk-{}".format(self.target_sdk)
        else:
            raise ValueError("Wrong data type of target_sdk!")

        plugin_file = "{}-{}.{}.{}".format(self.plugin_meta["id"],
                                           self.plugin_meta["version"],
                                           sdk_tag,
                                           result_extension)
        plugin_file = os.path.join(self.result_dir, plugin_file)
        return plugin_file

    def buildPackageFile(self, build_dir):
        archive_file = self.result_name
        if os.path.isfile(archive_file):
            os.remove(archive_file)

        zip_object = zipfile.ZipFile(archive_file, "w",
                                     compression = self.compression)

        zip_object.writestr("[Content_Types].xml", self.CONTENT_TYPES)
        zip_object.writestr("_rels/.rels", self.RELATION_BASE)
        zip_object.writestr("_rels/package.json.rels", self.RELATION_PLUGIN_BASE)

        for root, dirs, filenames in os.walk(build_dir):
            for file in filenames:
                filename = os.path.relpath(os.path.join(root, file), build_dir)
                print("d Packaging: {}".format(filename))
                filename_build = os.path.join(build_dir, filename)

                if "from_file" in dir(zipfile.ZipInfo):
                    fzipinfo = zipfile.ZipInfo.from_file(filename_build,
                                                         filename)
                    fzipinfo.external_attr = os.stat(filename_build)[ST_MODE] << 16
                    fopen = open(filename_build, "rb")
                    zip_object.writestr(fzipinfo,
                                        fopen.read(),
                                        compress_type = self.compression)
                    fopen.close()
                else:
                    zip_object.write(filename_build,
                                     filename
                                     )


        zip_object.close()
        print("i Package built: {}".format(archive_file))


class PluginCreator(CreatorCommon):
    "Creates plugin files based on plugin info (plugin.json)"
    # It is either or: ["umplugin", "curaplugin"] - using None here to provocate errors with os.path
    default_result_extension = None

    def __init__(self, args):
        super().__init__(args)
        self.plugin_location = self.source_dir
        self.package_location = None
        self.license_file = None

        # (optionally) Load package metadata
        self.package_meta = None
        if self.isPackageMeta():
            self.loadPackageMeta()
            self.package_location = self.plugin_location

    def verify(self):
        super().verify()

        # We might got pointed to an package source directory...
        if not self.checkValidSource():
            if self.package_meta:
                guessed_plugin_directory_in_package_source = os.path.join(self.source_dir, self.package_meta["package_id"])
                if self.checkValidSource(guessed_plugin_directory_in_package_source):
                    self.plugin_location = guessed_plugin_directory_in_package_source
            else:
                print("e Could not suggest an alternative plugin source location without any package metadata!")
                return False

        # Double-check..
        if not self.checkValidSource(self.plugin_location):
            print("e The provided source is not valid!")
            return False

        if not super().verify():
            return False

        return True

    def prepare(self):
        # Preparing build..
        self.prepareBuildDirectory(self.build_dir)

    def build(self):
        # Build all files.. Compile and copy them..
        self.compileAllPySources(self.plugin_location, self.build_dir, self.variant, optimize = args.optimize)
        self.copyOtherFiles(self.plugin_location, self.build_dir)
        print("d Installing license file")
        shutil.copy(self.license_file, self.build_dir)
        self.buildPluginMetadata(api = self.target_api)

    def bundle(self):
        # Building the package
        self.buildPluginFile(self.build_dir)

    def test(self):
        # Testing package
        self.testPackage()

    def clean(self):
        # Clean up build directory
        self.cleanUpBuildDirectory(self.build_dir)

    def checkValidSource(self, directory = None):
        if not directory:
            directory = self.source_dir

        # A plugin must be a folder
        if not os.path.isdir(directory):
            print("e Verify: Source location is not a directory!")
            return False
        print("d Verify: Found source at <{}>".format(directory))

        # A plugin must contain an __init__.py
        if not os.path.isfile(os.path.join(directory, "__init__.py")):
            print("e Verify: Found no __init__ file")
            return False
        print("d Verify: Found __init__ file")

        # .. and a plugin must contain an plugin.json!
        if not self.isPluginMeta(directory):
            print("e Verify: Found no plugin metadata")
            return False
        print("d Verify: Found plugin metadata")
        self.loadPluginMeta(directory)
        print("d Verify: Loaded plugin metadata")

        if not self.findLicenseFile(directory):
            print("e License not found!")
            return False

        # Checking whether all keywords are given in the metadata
        for keyword in essential_plugin_fields:
            if keyword not in self.plugin_meta.keys():
                print("e Missing keyword in plugin definition: {}".format(repr(keyword)))
                return False
            else:
                print("d Verify: Found keyword in {} definition.".format(repr(keyword)))

        # Checking API/SDK version
        if "minimum_api" in self.plugin_meta.keys():
            minimum_api = self.plugin_meta["minimum_api"]
        else:
            minimum_api = self.plugin_meta["api"]
        plugin_api_range = range(minimum_api, self.plugin_meta["api"] + 1)
        if not self.target_api in plugin_api_range:
            print("! ERROR: API/SDK {} is not within {}".format(self.target_api, repr(list(plugin_api_range))))
            return False

        print("i Verification passed!")

        return True

    def checkSourceImports(self, path):
        imports_cura = False
        imports_uranium = False
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                print("d Checking imports in file: {}".format(filename))
                filename = os.path.join(root, filename)
                extension = os.path.splitext(filename)[1]
                if extension in python_sources:
                    source_file = open(filename, errors='ignore')
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

    @property
    def result_name(self):
        if self._result_name:
            return self._result_name

        if self.result_extension:
            result_extension = self.result_extension
        else:
            result_extension = ["umplugin", "curaplugin"][self.checkSourceImports(self.plugin_location) is "cura"]

        plugin_file = "{}-{}.{}.{}".format(self.plugin_meta["id"],
                                           self.plugin_meta["version"],
                                           "api-{}".format(self.target_api),
                                           result_extension)
        plugin_file = os.path.join(self.result_dir, plugin_file)
        return plugin_file

    def buildPluginFile(self, build_dir):
        plugin_file = self.result_name
        if os.path.isfile(plugin_file):
            os.remove(plugin_file)

        zip_object = zipfile.ZipFile(plugin_file, "w",
                                     compression = self.compression)

        # Cura convention: Plugin inside the zip needs to be in a directory with the same name of the plugin itself.
        # Originally taken from Uranium:
        ## Ensure that the root folder is created correctly. We need to tell zip to not compress the folder!
        subdirectory = zipfile.ZipInfo(self.plugin_meta["id"] + "/")
        zip_object.writestr(subdirectory, "", compress_type = zipfile.ZIP_STORED) #Writing an empty string creates the directory.

        for root, dirs, filenames in os.walk(build_dir):
            for file in filenames:
                filename = os.path.relpath(os.path.join(root, file), build_dir)
                print("d Packaging: {}".format(filename))
                zip_object.write(os.path.join(build_dir, filename),
                                 os.path.join(self.plugin_meta["id"], filename)
                                 )
        print("i Package built: {}".format(plugin_file))

    def testPackage(self):
        plugin_file = self.result_name

        # Checking for the Cura conventions!
        with zipfile.ZipFile(plugin_file, "r") as zip_ref:
            plugin_id = None
            for file in zip_ref.infolist():
                if file.filename.endswith("/"):
                    plugin_id = file.filename.strip("/")
                    break

            if not plugin_id == self.plugin_meta["id"]:
                print("e Plugin name shall be {} and not {}!".format(repr(self.plugin_meta["id"]), repr(plugin_id)))
                return False

        # Checking whether license is present
        with zipfile.ZipFile(plugin_file, "r") as zip_ref:
            license_file_found = False
            for license_filename in license_filenames:
                license_path = os.path.join(plugin_id, license_filename)
                if license_path in [entry.filename for entry in zip_ref.infolist()]:
                    license_file_found = True

            if not license_file_found:
                print("e License file not found!")
                return False

        # Checking whether metadata is present
        with zipfile.ZipFile(plugin_file, "r") as zip_ref:
            metadata_path = os.path.join(plugin_id, plugin_metadata_filename)
            if not metadata_path in [entry.filename for entry in zip_ref.infolist()]:
                print("e Metadata file not found!")
                return False

        print("i Built plugin file is valid!")
        return True

class Package6Creator(PackageCreator):
    "Creates package files based on package info (package.json)"

    supported_formats = ["package6"]
    target_sdk = (6, 0, 0)
    default_result_extension = "curapackage"

class Package5Creator(PackageCreator):
    "Creates package files based on package info (package.json)"

    supported_formats = ["package5"]
    target_sdk = 5
    default_result_extension = "curapackage"

class Package4Creator(PackageCreator):
    "Creates package files based on package info (package.json)"

    supported_formats = ["package4"]
    target_sdk = 4
    default_result_extension = "curapackage"

class Plugin4Creator(PluginCreator):
    target_api = 4
    supported_formats = ["plugin4"]

class PluginSource4Creator(Plugin4Creator):
    default_result_extension = "zip"

    def __init__(self, args):
        super().__init__(args)
        # The following values are known to work well with Ultimaker's contributors portal
        self.result_extension = "zip"
        self.compression = zipfile.ZIP_DEFLATED
        self.variant = "source"

class PluginSourceCreator(PluginSource4Creator):
    "Creates a source archive, which can be uploaded to Ultimaker's contributors portal. This one is a plugin without any package info."
    target_sdk = None
    supported_formats = ["source"]

    def __init__(self, args):
        super().__init__(args)

    def checkValidSource(self, directory = None):
        if not super().checkValidSource(directory):
            return False

        if self.target_sdk:
            # Checking whether the targetted SDK version is supported.
            if not PackageCreator.checkValidPluginMetadata(self):
                return False

        return True

class PluginSource600Creator(PluginSourceCreator):
    "Creates a source archive, which can be uploaded to Ultimaker's contributors portal. This one is a plugin without any package info."
    target_sdk = (6, 0, 0)

creators = (Package6Creator, Package5Creator, Package4Creator, Plugin4Creator, PluginSourceCreator)
default_format = creators[0].supported_formats[0]
supported_formats = []
for creator in creators:
    supported_formats += creator.supported_formats
    del creator

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", "--cr", "-C",
                        dest="create",
                        type = str,
                        default = default_format,
                        choices = supported_formats + ["all"],
                        help = "Choose which creator to take to build your file")
    parser.add_argument("--source", "--src", "-s",
                        dest="source",
                        type = str,
                        default = "./source",
                        help = "Location of the source folder")
    parser.add_argument("--exclude", "--excl", "-e",
                        dest="exclude",
                        type = str,
                        default = None,
                        help = "Exclude files or directories separated via os.pathsep")
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
    parser.add_argument("--result", "--res", "-r",
                        dest="result",
                        type = str,
                        default = None,
                        help = "Name of the resulting file. Automatically generated if not set.")
    parser.add_argument("--variant", "--var", "-v",
                        dest="variant",
                        type = str,
                        default = "source",
                        choices = ["binary+source",
                                   "binary",
                                   "source",
                                   ],
                        help = "Variant of build")
    parser.add_argument("--compression", "--comp", "-c",
                        dest="compression",
                        type = str,
                        default = "zlib",
                        choices = ["none",
                                   "zlib",
                                   "bzip2",
                                   "lzma",
                                   ],
                        help = "Package compression")
    parser.add_argument("--optimize", "--opt", "-o",
                        dest="optimize",
                        type = int,
                        default = 0,
                        choices = range(3),
                        help = "Location of the build folder")
    parser.add_argument("--gitargs", "-ga",
                        dest="gitargs",
                        type = str,
                        default = "",
                        help = "git arguments")
    args = parser.parse_args()

    if args.create == "all":
        targets = supported_formats
    else:
        if args.create in supported_formats:
            targets = [args.create]
        else:
            print("Unsupported creator selected!")
            exit(1)

    args.source = getSource(args.source)
    if not args.source:
        print("Error: Source not found!")
        exit(1)

    for target in targets:
        for creator in creators:
            if target not in creator.supported_formats:
                continue
            creator = creator(args)
            if creator.verify():
                creator.prepare()
                creator.build()
                creator.bundle()
                creator.test()
                creator.clean()
    exit()
