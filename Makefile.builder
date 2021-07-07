RPM_SPEC_FILES := \
    rpm_spec/qubes-desktop-linux-menu.spec
DEBIAN_BUILD_DIRS := debian
RPM_BUILD_DEFINES.vm = --define "vm_package 1"
RPM_BUILD_DEFINES += $(RPM_BUILD_DEFINES.$(PACKAGE_SET))
