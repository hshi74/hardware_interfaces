include_directories(
  include
  ${Boost_INCLUDE_DIRS}
)

add_library(ATI_NETFT SHARED src/ati_netft.cpp src/netft_rdt_driver.cpp)
if(NOT RUT_INCLUDE_DIR)
  find_path(RUT_INCLUDE_DIR
    NAMES RobotUtilities/timer_linux.h
    HINTS ${CMAKE_INSTALL_PREFIX}/include /usr/local/include /usr/include
  )
endif()
if(NOT RUT_INCLUDE_DIR)
  message(FATAL_ERROR "RobotUtilities headers not found. Set CMAKE_PREFIX_PATH or install RobotUtilities.")
endif()
target_include_directories(ATI_NETFT PRIVATE ${RUT_INCLUDE_DIR})
target_link_libraries(ATI_NETFT ${Boost_LIBRARIES} ${RUT} ${YAMLLib})

pybind11_add_module(ati_netft_pybind 
  src/ati_netft_pybind.cpp
)
target_link_libraries(ati_netft_pybind PRIVATE
  ATI_NETFT
  ${Boost_LIBRARIES}
  ${RUT}
  ${YAMLLib}
)
target_include_directories(ati_netft_pybind PRIVATE ${RUT_INCLUDE_DIR})

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_PREFIX}/include/
)
install(TARGETS ATI_NETFT
    DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/
)

# set the output directory for the built module
set_target_properties(ati_netft_pybind PROPERTIES LIBRARY_OUTPUT_DIRECTORY python/)
set_target_properties(ati_netft_pybind PROPERTIES PREFIX "")
set_target_properties(ati_netft_pybind PROPERTIES OUTPUT_NAME "ati_netft_pybind")
