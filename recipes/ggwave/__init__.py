from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe


class GGWaveRecipe(CppCompiledComponentsPythonRecipe):
    """python-for-android recipe that builds the `ggwave` PyPI package."""

    version = "0.4.2"
    url = "https://pypi.python.org/packages/source/g/ggwave/ggwave-{version}.tar.gz"
    depends = ["setuptools"]
    call_hostpython_via_targetpython = False
    site_packages_name = "ggwave"


recipe = GGWaveRecipe()
