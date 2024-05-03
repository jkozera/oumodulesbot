#ifndef OUMODULES_BOT_VERIFY_ED25519_H_
#define OUMODULES_BOT_VERIFY_ED25519_H_

#include <array>
#include <cstddef>

namespace ou_modules_bot {

/* Copyright (c) 2022 Tero 'stedo' Liukko, MIT License */
constexpr unsigned char CHex_FromDigit(unsigned h) {
  return ((h & 0xf) + (h >> 6) * 9);
}

template <unsigned Len> constexpr auto HexDecode(const char hex[Len]) {
  std::array<unsigned char, Len / 2> bin = {};
  unsigned i = 0, j = 0;
  for (; j + 1 < Len; ++i, j += 2) {
    unsigned char hi = CHex_FromDigit(hex[j + 0]);
    unsigned char lo = CHex_FromDigit(hex[j + 1]);
    bin[i] = (hi << 4) | lo;
  }
  return bin;
}

bool VerifyEd25519(const unsigned char *pubkey, const char *sig_hex,
                   const char *msg, size_t msg_len);

} // namespace ou_modules_bot

#endif // OUMODULES_BOT_VERIFY_ED25519_H_
