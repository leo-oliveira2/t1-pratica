"""OpenBSD Blowfish password hashing.

This module implements the OpenBSD Blowfish password hashing
algorithm, as described in "A Future-Adaptable Password Scheme" by
Niels Provos and David Mazieres.

This system hashes passwords using a version of Bruce Schneier's Blowfish block cipher with modifications designed to raise the cost
of off-line password cracking. The computation cost of the algorithm
is parametised, so it can be increased as computers get faster.

Passwords are hashed using the hashpw() routine:

  hashpw(password, salt) -> hashed_password

Salts for the the second parameter may be randomly generated using the
gensalt() function:

  gensalt(log_rounds = 12) -> random_salt

The parameter "log_rounds" defines the complexity of the hashing. The
cost increases as 2**log_rounds.
"""

import base64
import os
import string
import struct

from eksblowfish import EksBlowfish


BCRYPT_VERSION = ('2', 'a')  # major, minor
BCRYPT_SALTLEN = 16          # expected raw salt length in Bytes.
BCRYPT_MAGICTEXT = 'OrpheanBeholderScryDoubt'   # Magic text to be enciphered.
BCRYPT_BLOCKS = len(BCRYPT_MAGICTEXT) * 8 / 32  # Ciphertext blocks
BCRYPT_MINROUNDS = 16        # Salt contains log2(rounds).

# bcrypt uses a strange base64 encoding, which is incompatible with the
# standard MIME way of doing it. Sigh.
B64_CHARS = ''.join((string.ascii_uppercase, string.ascii_lowercase,
                     string.digits, '+/'))
B64_CHARS_BCRYPT = ''.join(('./', string.ascii_uppercase,
                            string.ascii_lowercase, string.digits))
B64_TO_BCRYPT = string.maketrans(B64_CHARS, B64_CHARS_BCRYPT)
B64_FROM_BCRYPT = string.maketrans(B64_CHARS_BCRYPT, B64_CHARS)


def gensalt(log_rounds=12):
    """
    Generate a random text salt for use with hashpw(). "log_rounds"
    defines the complexity of the hashing, increasing the cost as
    2**log_rounds.
    """

    return _encode_salt(os.urandom(16), min(max(log_rounds, 4), 31))


def hashpw(password, salt):
    """
    hashpw(password, salt) -> hashed_password

    Hash the specified password and the salt using the OpenBSD Blowfish
    password hashing algorithm. Returns the hashed password along with the
    salt ($Vers$log2(NumRounds)$salt+passwd$), e.g.:

    $2$04$iwouldntknowwhattosayetKdJ6iFtacBqJdKe6aW7ou
    """


    (_, hash_ver, log_rounds, b64salt) = salt.split('$')
    (major, minor) = tuple(hash_ver)

    if (major, minor) > BCRYPT_VERSION:
        raise ValueError('Newer hash version than library version. OMG.')

    # Computing power doesn't increase linearly, 2^x should be fine.
    n = int(log_rounds);
    if n > 31 or n < 0:
        raise ValueError('Number of rounds out of bounds.')
    rounds = 1 << n  # Because 2 ** n is for wimps.
    if rounds < BCRYPT_MINROUNDS:
        raise ValueError('Minimum number of rounds is: %d' % BCRYPT_MINROUNDS)

    # Enforce (not base64-ed) minimum salt length.
    if (len(b64salt) * 3 / 4 != BCRYPT_SALTLEN):
        raise ValueError('Salt has invalid length.')

    # We don't want the base64 salt but the raw data.
    raw_salt = _b64_decode(b64salt)
    # Revision a of bcrypt adds a trailing \0 byte to the key.
    key_len = len(password) + (minor >= 'a' and 1 or 0);

    ## Set up EksBlowfish (this is the expensive part).
    bf = EksBlowfish()

    bf.expandkey(raw_salt, password, key_len)
    for k in xrange(rounds):
        # NB: The original bcrypt paper runs this step with the salt first,
        # then the password, not vice versa. The C implementation flips those,
        # which is why we reproduce the same bug here.
        bf.expandkey(0, password, key_len)
        bf.expandkey(0, raw_salt, BCRYPT_SALTLEN)

    ## Encrypt magic value, 64 times.
    # First, cut into 32bit integers. Big endian, again, sigh.
    bit_format = '>' + 'I' * BCRYPT_BLOCKS
    ctext = list(struct.unpack(bit_format, BCRYPT_MAGICTEXT))
    for i in xrange(64):
        # Encrypt blocks pairwise.
        for d in xrange(0, BCRYPT_BLOCKS, 2):
            ctext[d], ctext[d+1] = bf.cipher(ctext[d], ctext[d+1], bf.ENCRYPT)

    ## Concatenate cost, salt, result, and return.
    # The C implementation cuts off the last byte of the ciphertext, so we do
    # the same.
    result = _b64_encode(struct.pack(bit_format, *ctext)[:-1])
    return salt + result


def _encode_salt(csalt, log_rounds):
    """"
    encode_salt(csalt, log_rounds) -> encoded_salt

    Encode a raw binary salt and the specified log2(rounds) as a
    standard bcrypt text salt.
    """

    if len(csalt) != BCRYPT_SALTLEN:
        raise ValueError("Invalid salt length")

    if log_rounds < 4 or log_rounds > 31:
        raise ValueError("Invalid number of rounds")

    salt = '${maj}{min}${log_rounds:02d}${b64salt}'.format(
        maj=BCRYPT_VERSION[0], min=BCRYPT_VERSION[1], log_rounds=log_rounds,
        b64salt=_b64_encode(csalt))

    return salt


def _b64_encode(data):
    """
    base64 encode wrapper.

    Uses alternative chars and removes base 64 padding.
    """
    enc = base64.b64encode(data)
    return enc.translate(B64_TO_BCRYPT, '=')


def _b64_decode(data):
    """
    base64 decode wrapper.

    Uses alternative chars and handles possibly missing padding.
    """
    encoded = data.translate(B64_FROM_BCRYPT)
    padding = '=' * (4 - len(data) % 4) if len(data) % 4 else ''
    return base64.b64decode(encoded + padding)