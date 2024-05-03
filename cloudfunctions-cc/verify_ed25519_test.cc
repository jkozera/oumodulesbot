#include <array>
#include <gtest/gtest.h>

#include "verify_ed25519.h"

using ou_modules_bot::HexDecode;
using ou_modules_bot::VerifyEd25519;

TEST(VerifyEd25519Test, ValidSignature) {
  char public_key[] = ("168544f25101a8d47ce15cae78a6b655"
                       "26f5456fb57cdd2279c4167b22af3fb1");
  auto pk = HexDecode<64>(public_key);

  std::string message = "some_message";
  std::string signature = ("3759625910b41f02e219d72aa171a714"
                           "f455d50c56fdec84bb725e305de9b285"
                           "174ccd27d5af53c8af5308db5ea44fe1"
                           "5985f1b451d2ae797f2959335c49d805");

  EXPECT_TRUE(VerifyEd25519(pk.data(), signature.c_str(), message.c_str(),
                            message.size()));
}

TEST(VerifyEd25519Test, InvalidSignature) {
  char public_key[] = ("168544f25101a8d47ce15cae78a6b655"
                       "26f5456fb57cdd2279c4167b22af3fb1");
  auto pk = HexDecode<64>(public_key);
  std::string message = "your_message";
  std::string signature = ("0759625910b41f02e219d72aa171a714"
                           "f455d50c56fdec84bb725e305de9b285"
                           "174ccd27d5af53c8af5308db5ea44fe1"
                           "5985f1b451d2ae797f2959335c49d805");

  EXPECT_FALSE(VerifyEd25519(pk.data(), signature.c_str(), message.c_str(),
                             message.size()));
}

// Add more test cases as needed

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
