from cx_Freeze import setup, Executable

# Dependency fine tuning.
build_exe_options = {"optimize" : 2,
                     "include_msvcr": True,}

# console application
base = None

setup(name = "cpo",
      version = "0.0.1",
      description = "CuraPluginOven",
      options = {"build_exe": build_exe_options,
                 },
      executables = [Executable("cpo.py",
                                base = base,
                                copyright = "Thomas Karl Pietrowski"),
                    ]
      )