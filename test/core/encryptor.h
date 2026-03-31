#ifndef ENCRYPTOR_H
#define ENCRYPTOR_H

typedef struct {
    char *key;
    int key_length;
} VaultKey;

int encrypt_data(const char *input, char *output, VaultKey key);

#endif