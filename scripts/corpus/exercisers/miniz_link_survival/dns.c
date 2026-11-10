/* control: the DNS variant's use, compress/uncompress/compressBound (never run) */
#include "miniz.h"
int main(int argc, char **argv)
{
    unsigned char in[64] = {0}, out[128], back[64];
    mz_ulong n = compressBound(sizeof in), m = sizeof back;
    (void)argv;
    if (argc > 1) {
        compress(out, &n, in, sizeof in);
        uncompress(back, &m, out, n);
    }
    return (int)(n + m);
}
