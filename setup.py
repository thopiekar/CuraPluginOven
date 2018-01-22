from cx_Freeze import setup, Executable

# Dependency fine tuning.
build_exe_options = {}

# console application
base = None

setup(name = "cpo",
      version = "0.0.1",
      description = "CuraPluginOven",
      options = {"build_exe": build_exe_options},
      executables = [Executable("cpo.py",
                                base = base),
                    ]
      )