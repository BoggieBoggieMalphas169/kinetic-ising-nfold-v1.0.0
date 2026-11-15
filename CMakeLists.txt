cmake_minimum_required(VERSION 3.16)
project(kinetic_ising_nfold C)

# The validated C simulation engine lives in simulator/.
# Its targets are exported unchanged into the top-level build.
enable_testing()
add_subdirectory(simulator)
