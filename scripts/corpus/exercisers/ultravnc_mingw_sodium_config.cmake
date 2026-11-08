get_filename_component(_uvnc_pfx "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
if(NOT TARGET unofficial-sodium::sodium)
  add_library(unofficial-sodium::sodium STATIC IMPORTED)
  set_target_properties(unofficial-sodium::sodium PROPERTIES
    IMPORTED_LOCATION "${_uvnc_pfx}/lib/libsodium.a"
    INTERFACE_INCLUDE_DIRECTORIES "${_uvnc_pfx}/include"
    INTERFACE_COMPILE_DEFINITIONS SODIUM_STATIC)
endif()
set(unofficial-sodium_FOUND TRUE)
