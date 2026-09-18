"""Decoder for lz-string's URI-safe encoding (decompressFromEncodedURIComponent).

BSSDB stores a whole deck in its share links as lz-string compressed JSON. This
is a direct port of the JavaScript library's decompressor (MIT licensed,
https://github.com/pieroxy/lz-string), kept here so the plugin needs no extra
dependency.
"""

URI_SAFE_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$'
_BASE_VALUES = {char: index for index, char in enumerate(URI_SAFE_ALPHABET)}


class _BitReader:
    def __init__(self, text: str, reset_value: int):
        self.text = text
        self.reset_value = reset_value
        self.value = self._char_value(0)
        self.position = reset_value
        self.index = 1

    def _char_value(self, index: int) -> int:
        if index >= len(self.text):
            return 0
        char = self.text[index]
        if char not in _BASE_VALUES:
            raise ValueError(f'"{char}" is not valid in an lz-string encoded value')
        return _BASE_VALUES[char]

    def read(self, bit_count: int) -> int:
        bits = 0
        power = 1
        for _ in range(bit_count):
            bit = self.value & self.position
            self.position >>= 1
            if self.position == 0:
                self.position = self.reset_value
                self.value = self._char_value(self.index)
                self.index += 1
            if bit:
                bits |= power
            power <<= 1
        return bits


def decompress_from_encoded_uri_component(encoded: str):
    """Return the decompressed string, or None if `encoded` is not valid lz-string data."""
    if encoded is None:
        return ''
    if encoded == '':
        return None

    # A '+' in a URL often arrives as a space.
    text = encoded.replace(' ', '+')
    reader = _BitReader(text, 32)

    dictionary = {0: 0, 1: 1, 2: 2}
    enlarge_in = 4
    dict_size = 4
    num_bits = 3

    first = reader.read(2)
    if first == 0:
        char = chr(reader.read(8))
    elif first == 1:
        char = chr(reader.read(16))
    else:
        return ''

    dictionary[3] = char
    word = char
    result = [char]

    while True:
        if reader.index > len(text):
            return ''

        code = reader.read(num_bits)
        if code == 0 or code == 1:
            dictionary[dict_size] = chr(reader.read(8 if code == 0 else 16))
            dict_size += 1
            code = dict_size - 1
            enlarge_in -= 1
        elif code == 2:
            return _join_utf16(result)

        if enlarge_in == 0:
            enlarge_in = 2 ** num_bits
            num_bits += 1

        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size:
            entry = word + word[0]
        else:
            return None

        result.append(entry)
        dictionary[dict_size] = word + entry[0]
        dict_size += 1
        enlarge_in -= 1
        word = entry

        if enlarge_in == 0:
            enlarge_in = 2 ** num_bits
            num_bits += 1


def _join_utf16(parts) -> str:
    # lz-string works on UTF-16 code units, so characters outside the Basic
    # Multilingual Plane arrive as surrogate pairs. Recombine them.
    joined = ''.join(parts)
    return joined.encode('utf-16', 'surrogatepass').decode('utf-16')
