# Included right after XMRig's project() call through
# -DCMAKE_PROJECT_xmrig_INCLUDE by recipes/xmrig_msvc.py
# (XMRig_6.25.0-gpu-hwloc_msvc).
#
# On MSVC XMRig's src/backend/cpu/cpu.cmake calls
# add_subdirectory(src/3rdparty/hwloc), which builds its vendored hwloc as a
# static library target named `hwloc`, and then links `hwloc`; there is no
# option for an external hwloc. This replaces that one call with an imported
# target of the same name: the hwloc 2.12.1 DLL the recipe built from the
# release tarball (XM_HWLOC_IMPLIB, XM_HWLOC_DLL). Every other
# add_subdirectory call goes to the built-in command unchanged. No XMRig file
# is modified.
if (NOT EXISTS "${XM_HWLOC_IMPLIB}")
    message(FATAL_ERROR "XM_HWLOC_IMPLIB does not exist: ${XM_HWLOC_IMPLIB}")
endif()

function(add_subdirectory source_dir)
    if (source_dir STREQUAL "src/3rdparty/hwloc")
        add_library(hwloc SHARED IMPORTED GLOBAL)
        set_target_properties(hwloc PROPERTIES
            IMPORTED_IMPLIB "${XM_HWLOC_IMPLIB}"
            IMPORTED_LOCATION "${XM_HWLOC_DLL}")
        message(STATUS "hwloc: the imported DLL ${XM_HWLOC_IMPLIB}, not src/3rdparty/hwloc")
    else()
        _add_subdirectory(${ARGV})
    endif()
endfunction()
