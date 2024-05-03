cmake_minimum_required(VERSION 3.24)

project(OUBotInteractions)

find_package(google_cloud_cpp_pubsub CONFIG REQUIRED)
find_package(functions_framework_cpp REQUIRED)
find_package(nlohmann_json 3.11.2 REQUIRED)
find_package(OpenSSL REQUIRED)

add_library(functions_framework_cpp_function
 interaction.cc interaction_lib.cc verify_ed25519.cc)
target_link_libraries(
    functions_framework_cpp_function
    functions-framework-cpp::framework
    google-cloud-cpp::pubsub google-cloud-cpp::pubsub_protos
    nlohmann_json::nlohmann_json
    OpenSSL::Crypto)

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(
    interaction_lib_test interaction_lib_test.cc interaction_lib.cc
)
target_link_libraries(
    interaction_lib_test GTest::gtest_main nlohmann_json::nlohmann_json
)

add_executable(
    verify_ed25519_test verify_ed25519_test.cc verify_ed25519.cc
)
target_link_libraries(
    verify_ed25519_test GTest::gtest_main OpenSSL::Crypto
)

include(GoogleTest)
gtest_discover_tests(interaction_lib_test)
