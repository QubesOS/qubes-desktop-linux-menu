#!/usr/bin/env python3
"""Setup.py file"""
import setuptools.command.install

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
)
