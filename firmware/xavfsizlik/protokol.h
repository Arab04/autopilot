/*
 * Jetson <-> xavfsizlik platasi aloqa protokoli (UART, 115200).
 *
 * Kadr: A5 5A | uzunlik | tur | seq | ma'lumot (uzunlik bayt) | CRC16-CCITT (uzunlikdan ma'lumot oxirigacha, katta bayt avval)
 *
 * tur 0x01, Jetson -> plata, buyruq (4 bayt, kichik bayt avval):
 *     int16 tezlik (sm/s) | uint8 tormoz (0,1 m/s^2) | uint8 bayroqlar
 *     bayroqlar: bit0 operator_toxtat, bit1 operator_ochish, bit2 tez_yol, bit3 aloqa_bor
 * tur 0x81, plata -> Jetson, holat (10 bayt):
 *     uint8 holat | uint16 sabab | int16 tezlik_max (sm/s) | int16 tezlik (sm/s) | uint16 kuchlanish (0,01 V) | uint8 yon_gildirak
 *
 * Shovqinli liniyada: CRC xato kadr tashlanadi, parser keyingi A5 5A dan davom etadi; takroriy yoki eski
 * seq li kadr qabul qilinmaydi (Jetson har kadrda seq ni 1 ga oshiradi, 0..255 aylanadi).
 * Buyruq kelmay qolsa, xavfsizlik.c 120 ms dan keyin skuterni to'xtatadi.
 */
#ifndef PROTOKOL_H
#define PROTOKOL_H

#include <stddef.h>
#include <stdint.h>

#include "xavfsizlik.h"

#define XP_BOSH1 0xA5
#define XP_BOSH2 0x5A
#define XP_TUR_BUYRUQ 0x01
#define XP_TUR_HOLAT 0x81
#define XP_MAX_MALUMOT 32
#define XP_MAX_KADR (XP_MAX_MALUMOT + 7)

typedef struct {
    uint8_t bosqich, uzunlik, tur, seq, i;
    uint8_t malumot[XP_MAX_MALUMOT];
    uint16_t crc;
    uint8_t oxirgi_seq;
    uint8_t seq_bor;
    uint32_t kadrlar, crc_xato, seq_xato;
} XpParser;

uint16_t xp_crc16(const uint8_t *p, size_t n, uint16_t crc);
void xp_boshlash(XpParser *p);
/* Bitta bayt beriladi. To'g'ri, yangi buyruq kadri tugasa 1 qaytaradi va *b ni to'ldiradi. */
int xp_bayt(XpParser *p, uint8_t bayt, XvBuyruq *b);
size_t xp_buyruq_yoz(uint8_t seq, const XvBuyruq *b, uint8_t *kadr);
size_t xp_holat_yoz(uint8_t seq, const XvChiqish *c, float tezlik, float kuchlanish, uint8_t yon_gildirak,
                    uint8_t *kadr);

#endif
