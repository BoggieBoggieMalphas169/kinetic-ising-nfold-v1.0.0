cmake_minimum_required(VERSION 3.16)
project(ising_tracing C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# An overlay: the historical engine and its frozen release hashes stay untouched.
add_library(ising_trace_core
    ../src/ising.c
    ../src/rng.c
    ../src/dynamics.c
    src/standard_mc.c
    src/nfold.c
    src/trace.c
)
target_include_directories(ising_trace_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
)
if(NOT MSVC)
    target_link_libraries(ising_trace_core PUBLIC m)
    target_compile_options(ising_trace_core PRIVATE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)
else()
    target_compile_options(ising_trace_core PRIVATE /W4)
endif()
add_executable(ising_standard_trace src/main_standard.c)
target_link_libraries(ising_standard_trace PRIVATE ising_trace_core)
add_executable(ising_nfold_trace src/main_nfold.c)
target_link_libraries(ising_nfold_trace PRIVATE ising_trace_core)

enable_testing()
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    add_test(NAME trace_integration
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_trace_integration.py
            --standard $<TARGET_FILE:ising_standard_trace>
            --nfold $<TARGET_FILE:ising_nfold_trace>)
endif()
