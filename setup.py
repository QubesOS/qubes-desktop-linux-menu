#!/usr/bin/env python3
"""Setup.py file"""

import os
import subprocess
import setuptools.command.install


# create and install translation files
class InstallWithLocale(setuptools.command.install.install):
    """Install command that also compiles and installs .mo files"""

    def create_mo_files(self):
        """Compile locale/*/LC_MESSAGES/*.po into the install root"""
        data_files = []
        localedir = "locale"
        po_dirs = [
            localedir + "/" + l + "/LC_MESSAGES/"
            for l in next(os.walk(localedir))[1]
        ]
        for d in po_dirs:
            mo_dir = os.path.join(self.root or "/", "usr/share", d)
            os.makedirs(mo_dir, exist_ok=True)
            mo_files = []
            po_files = [
                f
                for f in next(os.walk(d))[2]
                if os.path.splitext(f)[1] == ".po"
            ]
            for po_file in po_files:
                filename, _extension = os.path.splitext(po_file)
                mo_file = filename + ".mo"
                subprocess.check_call(
                    ["msgfmt", d + po_file, "-o", os.path.join(mo_dir, mo_file)]
                )
                mo_files.append(d + mo_file)
            data_files.append((d, mo_files))
        return data_files

    def run(self):
        """Compile translations, then run the regular install"""
        self.create_mo_files()
        super().run()


setuptools.setup(
    name="qubes_menu",
    version="0.1",
    author="Invisible Things Lab",
    author_email="marmarta@invisiblethingslab.com",
    description="Qubes App Menu",
    license="GPL2+",
    url="https://www.qubes-os.org/",
    packages=["qubes_menu", "qubes_menu_settings"],
    entry_points={
        "gui_scripts": [
            "qubes-app-menu = qubes_menu.appmenu:main",
            "qubes-appmenu-settings = qubes_menu_settings.menu_settings:main",
        ]
    },
    package_data={
        "qubes_menu": [
            "qubes-menu.glade",
            "qubes-menu-dark.css",
            "qubes-menu-light.css",
            "qubes-menu-base.css",
        ],
        "qubes_menu_settings": ["menu_settings.glade", "menu_settings.css"],
    },
    cmdclass={"install": InstallWithLocale},
)
