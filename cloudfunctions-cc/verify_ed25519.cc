
#include <array>
#include <openssl/evp.h>
#include <openssl/err.h>

#include "verify_ed25519.h"

namespace ou_modules_bot {

bool VerifyEd25519(const unsigned char *pubkey, const char *sig_hex,
                   const char *msg, size_t msg_len) {
  EVP_PKEY *pk =
      EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519, nullptr, pubkey, 32);
  EVP_MD_CTX *md_ctx = EVP_MD_CTX_new();
  bool success = false;
  if (EVP_DigestVerifyInit(md_ctx, nullptr, nullptr, nullptr, pk) == 1) {
    auto sig_bytes = HexDecode<128>(sig_hex);
    success = (EVP_DigestVerify(md_ctx, sig_bytes.data(), 64,
                                (const unsigned char *)msg, msg_len) == 1);
  }
  EVP_MD_CTX_free(md_ctx);
  EVP_PKEY_free(pk);

  return success;
}

} // namespace ou_modules_bot