from distutils.core import setup

setup(
    # Application name:
    name="fecfile-ImageGenerator",

    # Version number (initial):
    version="1.0.0",

    # Packages
    packages=["fecfile-ImageGenerator"],

    # Include additional files into the package
    include_package_data=True,

    # license="LICENSE.txt",
    description="This project is an API for FECFile Image Generation project",

    # Dependent packages (distributions)
    install_requires=[
        "flask",
    ],
)
