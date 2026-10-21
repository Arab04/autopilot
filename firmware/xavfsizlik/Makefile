CC ?= gcc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Werror -Wconversion -Wno-sign-conversion
MANBA = xavfsizlik.c protokol.c

test: test_xavfsizlik
	./test_xavfsizlik

test_xavfsizlik: $(MANBA) test_xavfsizlik.c xavfsizlik.h protokol.h
	$(CC) $(CFLAGS) -fsanitize=address,undefined -o $@ $(MANBA) test_xavfsizlik.c -lm

# Python simulyatori uchun (ctypes)
libxavfsizlik.so: $(MANBA) xavfsizlik.h protokol.h
	$(CC) $(CFLAGS) -shared -fPIC -o $@ $(MANBA) -lm

clean:
	rm -f test_xavfsizlik libxavfsizlik.so

.PHONY: test clean
