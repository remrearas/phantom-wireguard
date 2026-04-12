"""
Bundled wstunnel binaries.

This directory ships the wstunnel release tarballs for each
supported architecture; the setup module extracts them at install
time. To bump the version: run the ``ARAS-Workspace/wstunnel``
"Release Linux" workflow, place the new
``wstunnel_<VERSION>_linux_amd64.tar.gz`` and
``wstunnel_<VERSION>_linux_arm64.tar.gz`` files here, and update
``WSTUNNEL_VERSION`` in
``phantom_frontmatter/modules/setup/lib/binary_utils.py`` in the
same commit.
"""
