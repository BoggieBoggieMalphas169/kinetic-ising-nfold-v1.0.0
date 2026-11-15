cmake_minimum_required(VERSION 3.16)
project(ising_validation C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(ISING_ENABLE_SANITIZERS "Enable AddressSanitizer and UBSan (GCC/Clang)" OFF)
option(ISING_STRICT_WARNINGS "Enable extra compiler warnings" ON)

add_library(ising_core
    src/rng.c
    src/ising.c
    src/dynamics.c
    src/standard_mc.c
    src/nfold.c
)
target_include_directories(ising_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

if(NOT MSVC)
    target_link_libraries(ising_core PUBLIC m)
endif()

if(ISING_STRICT_WARNINGS)
    if(MSVC)
        target_compile_options(ising_core PRIVATE /W4)
    else()
        target_compile_options(ising_core PRIVATE
            -Wall -Wextra -Wpedantic -Wshadow -Wconversion
        )
    endif()
endif()

if(ISING_ENABLE_SANITIZERS AND NOT MSVC)
    target_compile_options(ising_core PUBLIC
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
    )
    target_link_options(ising_core PUBLIC
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
    )
endif()

add_executable(ising_standard src/main_standard.c)
target_link_libraries(ising_standard PRIVATE ising_core)

add_executable(ising_nfold src/main_nfold.c)
target_link_libraries(ising_nfold PRIVATE ising_core)

# Optional observability runner for Level-2 plots. Does not alter production binaries.
add_executable(ising_trace src/main_trace.c)
target_link_libraries(ising_trace PRIVATE ising_core)

enable_testing()

add_executable(test_physics tests/test_physics.c)
target_link_libraries(test_physics PRIVATE ising_core)
add_test(NAME physics COMMAND test_physics)

add_executable(test_nfold tests/test_nfold.c)
target_link_libraries(test_nfold PRIVATE ising_core)
add_test(NAME nfold COMMAND test_nfold)

find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    add_test(
        NAME smoke_standard
        COMMAND ising_standard
            --L 8 --T 1.5 --J 1 --H -3 --runs 32 --seed 1234
            --dynamics glauber
            --output ${CMAKE_CURRENT_BINARY_DIR}/smoke_standard.csv
    )
    add_test(
        NAME smoke_nfold
        COMMAND ising_nfold
            --L 8 --T 1.5 --J 1 --H -3 --runs 32 --seed 1234
            --dynamics glauber
            --output ${CMAKE_CURRENT_BINARY_DIR}/smoke_nfold.csv
    )
    add_test(
        NAME smoke_csv_standard
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_csv_invariants.py
            ${CMAKE_CURRENT_BINARY_DIR}/smoke_standard.csv
            --require-complete
    )
    set_tests_properties(smoke_csv_standard PROPERTIES DEPENDS smoke_standard)

    add_test(
        NAME smoke_csv_nfold
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_csv_invariants.py
            ${CMAKE_CURRENT_BINARY_DIR}/smoke_nfold.csv
            --require-complete
    )
    set_tests_properties(smoke_csv_nfold PROPERTIES DEPENDS smoke_nfold)
endif()
