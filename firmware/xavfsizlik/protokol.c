#include "protokol.h"

#include <math.h>

uint16_t xp_crc16(const uint8_t *p, size_t n, uint16_t crc)
{
    /* CRC-16/CCITT-FALSE: polinom 0x1021, boshlang'ich 0xFFFF */
    while (n--) {
        crc = (uint16_t)(crc ^ (uint16_t)(*p++ << 8));
        for (int i = 0; i < 8; i++) crc = (uint16_t)((crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
    }
    return crc;
}

void xp_boshlash(XpParser *p)
{
    *p = (XpParser){0};
}

static int16_t sm(float v)
{
    float x = roundf(v * 100.0f);
    return (int16_t)(x > 32767 ? 32767 : x < -32768 ? -32768 : x);
}

static void yoz16(uint8_t *q, uint16_t x) { q[0] = (uint8_t)x; q[1] = (uint8_t)(x >> 8); }
static uint16_t oqi16(const uint8_t *q) { return (uint16_t)(q[0] | (q[1] << 8)); }

static size_t kadr_yoz(uint8_t tur, uint8_t seq, const uint8_t *m, uint8_t n, uint8_t *k)
{
    k[0] = XP_BOSH1; k[1] = XP_BOSH2; k[2] = n; k[3] = tur; k[4] = seq;
    for (uint8_t i = 0; i < n; i++) k[5 + i] = m[i];
    uint16_t crc = xp_crc16(k + 2, (size_t)n + 3, 0xFFFF);
    k[5 + n] = (uint8_t)(crc >> 8);
    k[6 + n] = (uint8_t)crc;
    return (size_t)n + 7;
}

size_t xp_buyruq_yoz(uint8_t seq, const XvBuyruq *b, uint8_t *kadr)
{
    uint8_t m[4];
    yoz16(m, (uint16_t)sm(b->tezlik));
    float t = roundf(b->tormoz * 10.0f);
    m[2] = (uint8_t)(t < 0 ? 0 : t > 255 ? 255 : t);
    m[3] = (uint8_t)((b->operator_toxtat ? 1 : 0) | (b->operator_ochish ? 2 : 0) | (b->tez_yol ? 4 : 0)
                     | (b->aloqa_bor ? 8 : 0));
    return kadr_yoz(XP_TUR_BUYRUQ, seq, m, 4, kadr);
}

size_t xp_holat_yoz(uint8_t seq, const XvChiqish *c, float tezlik, float kuchlanish, uint8_t yon_gildirak,
                    uint8_t *kadr)
{
    uint8_t m[10];
    m[0] = (uint8_t)c->holat;
    yoz16(m + 1, (uint16_t)c->sabab);
    yoz16(m + 3, (uint16_t)sm(c->tezlik_max));
    yoz16(m + 5, (uint16_t)sm(tezlik));
    float u = roundf(kuchlanish * 100.0f);
    yoz16(m + 7, (uint16_t)(u < 0 ? 0 : u > 65535 ? 65535 : u));
    m[9] = yon_gildirak;
    return kadr_yoz(XP_TUR_HOLAT, seq, m, 10, kadr);
}

int xp_bayt(XpParser *p, uint8_t bayt, XvBuyruq *b)
{
    switch (p->bosqich) {
    case 0: if (bayt == XP_BOSH1) p->bosqich = 1; return 0;
    case 1: p->bosqich = bayt == XP_BOSH2 ? 2 : (bayt == XP_BOSH1 ? 1 : 0); return 0;
    case 2:
        if (bayt > XP_MAX_MALUMOT) { p->bosqich = bayt == XP_BOSH1 ? 1 : 0; return 0; }
        p->uzunlik = bayt; p->crc = xp_crc16(&bayt, 1, 0xFFFF); p->bosqich = 3; return 0;
    case 3: p->tur = bayt; p->crc = xp_crc16(&bayt, 1, p->crc); p->bosqich = 4; return 0;
    case 4:
        p->seq = bayt; p->crc = xp_crc16(&bayt, 1, p->crc); p->i = 0;
        p->bosqich = p->uzunlik ? 5 : 6; return 0;
    case 5:
        p->malumot[p->i++] = bayt; p->crc = xp_crc16(&bayt, 1, p->crc);
        if (p->i >= p->uzunlik) p->bosqich = 6;
        return 0;
    case 6:
        if (bayt != (uint8_t)(p->crc >> 8)) { p->crc_xato++; p->bosqich = bayt == XP_BOSH1 ? 1 : 0; return 0; }
        p->bosqich = 7; return 0;
    case 7:
        p->bosqich = 0;
        if (bayt != (uint8_t)p->crc) { p->crc_xato++; if (bayt == XP_BOSH1) p->bosqich = 1; return 0; }
        break;
    default: p->bosqich = 0; return 0;
    }
    /* Butun kadr to'g'ri */
    if (p->tur != XP_TUR_BUYRUQ || p->uzunlik != 4) return 0;
    uint8_t farq = (uint8_t)(p->seq - p->oxirgi_seq);
    if (p->seq_bor && (farq == 0 || farq > 127)) { p->seq_xato++; return 0; }  /* takroriy yoki eski */
    p->seq_bor = 1;
    p->oxirgi_seq = p->seq;
    p->kadrlar++;
    b->tezlik = (int16_t)oqi16(p->malumot) / 100.0f;
    b->tormoz = p->malumot[2] / 10.0f;
    b->operator_toxtat = p->malumot[3] & 1;
    b->operator_ochish = (p->malumot[3] >> 1) & 1;
    b->tez_yol = (p->malumot[3] >> 2) & 1;
    b->aloqa_bor = (p->malumot[3] >> 3) & 1;
    return 1;
}
