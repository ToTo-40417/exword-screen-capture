/* EX-word 1RC2 is big-endian RGB565, independent of the host byte order. */
void brain_rgb565(const unsigned char *src, unsigned char *dst, unsigned int count)
{
    unsigned int i;
    for (i = 0; i < count; ++i) {
        unsigned int value = ((unsigned int)src[2 * i] << 8) | src[2 * i + 1];
        unsigned int r = (value >> 11) & 31;
        unsigned int g = (value >> 5) & 63;
        unsigned int b = value & 31;
        dst[3 * i] = (unsigned char)((r << 3) | (r >> 2));
        dst[3 * i + 1] = (unsigned char)((g << 2) | (g >> 4));
        dst[3 * i + 2] = (unsigned char)((b << 3) | (b >> 2));
    }
}
