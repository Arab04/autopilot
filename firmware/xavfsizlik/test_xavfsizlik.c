/* Xavfsizlik platasi dasturi sinovlari (kompyuterda): make test */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "protokol.h"
#include "xavfsizlik.h"

static int xatolar = 0, sinovlar = 0;
#define TEKSHIR(shart, ...) do { sinovlar++; if (!(shart)) { xatolar++; printf("  XATO %s:%d: ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); } } while (0)

#define KMH (1.0f / 3.6f)
#define GRAD (3.14159265f / 180.0f)

/* Oddiy skuter: motor tezlik_max gacha 1,5 m/s^2 bilan tezlanadi, tormoz bilan sekinlashadi */
typedef struct {
    XvHolat h;
    XvKirish k;
    XvChiqish c;
    float v_buyruq;     /* motor kontrolleri ko'rgan buyruq */
} Skuter;

static void yangi(Skuter *s)
{
    XvSozlama z;
    xv_standart_sozlama(&z);
    xv_boshlash(&s->h, &z);
    memset(&s->k, 0, sizeof(s->k));
    for (int i = 0; i < XV_ULTRATOVUSH_SONI; i++) s->k.ultratovush[i] = 5.0f;
    s->k.kuchlanish = 50.0f;
    s->k.tok_bor = true;
    s->k.buyruq = (XvBuyruq){.tezlik = 5.0f, .tormoz = 2.5f, .tez_yol = true, .aloqa_bor = true};
    s->k.t_ms = 1000;
    memset(&s->c, 0, sizeof(s->c));
}

/* 10 ms qadam; jetson = shu qadamda buyruq kadri keldimi */
static void qadam(Skuter *s, int jetson, int fizika)
{
    s->k.buyruq_yangi = jetson;
    xv_qadam(&s->h, &s->k, &s->c);
    s->k.buyruq.operator_ochish = false;
    if (fizika) {
        float maqsad = s->c.motor_uzish ? 0.0f : s->c.tezlik_max;
        float v = s->k.tezlik;
        if (v < maqsad) v = fminf(maqsad, v + 1.5f * 0.01f);
        else if (v > maqsad) v = fmaxf(maqsad, v - fmaxf(s->c.tormoz, 0.3f) * 0.01f);
        s->k.tezlik = v;
    }
    s->k.t_ms += 10;
}

static void yur(Skuter *s, float soniya, int jetson_har, int fizika)
{
    int n = (int)(soniya * 100 + 0.5f);
    for (int i = 0; i < n; i++) qadam(s, jetson_har > 0 && i % jetson_har == 0, fizika);
}

static void sinov_oddiy(void)
{
    Skuter s; yangi(&s);
    yur(&s, 5, 5, 1);
    TEKSHIR(s.c.holat == XV_NORMAL && fabsf(s.c.tezlik_max - 5.0f) < 1e-3, "holat %d, max %.2f", s.c.holat, s.c.tezlik_max);
    TEKSHIR(fabsf(s.k.tezlik - 5.0f) < 0.01f, "tezlik %.2f", s.k.tezlik);
    s.k.buyruq.tezlik = 10.0f;
    yur(&s, 0.1f, 5, 0);
    TEKSHIR(fabsf(s.c.tezlik_max - 20 * KMH) < 1e-3, "20 km/soat chegarasi: %.2f", s.c.tezlik_max);
    /* Datchik eng uzoq masofasini (aks-sado yo'q) ko'rsatsa, 20 km/soatda ham tormoz bermaydi:
     * bu tezlikda to'xtash yo'li (4,6 m) datchik masofasidan (4,5 m) uzun */
    yur(&s, 6, 5, 1);
    TEKSHIR(s.c.holat == XV_NORMAL && s.k.tezlik > 5.5f, "bo'sh yo'lda 20 km/soat: holat %d, v %.2f", s.c.holat, s.k.tezlik);
}

static void sinov_yoqilganda(void)
{
    Skuter s; yangi(&s);
    yur(&s, 1, 0, 1);  /* Jetson hali gapirmagan */
    TEKSHIR(s.c.tezlik_max == 0 && s.k.tezlik == 0, "Jetsonsiz yurmaydi");
}

static void sinov_ultratovush(void)
{
    /* 5,5 m/s (20 km/soat) da oldinda turgan narsaga yaqinlashadi: urilmasdan to'xtashi kerak */
    Skuter s; yangi(&s);
    s.k.buyruq.tezlik = 20 * KMH;
    yur(&s, 6, 5, 1);
    float tosiq = 40.0f, yol = 0;
    int favq = 0;
    for (int i = 0; i < 2000; i++) {
        float d = tosiq - yol;
        for (int j = 0; j < XV_OLDINGI_SONI; j++) s.k.ultratovush[j] = d > 4.5f ? 4.5f : d;  /* JSN-SR04T ~4,5 m */
        qadam(&s, i % 5 == 0, 1);
        yol += s.k.tezlik * 0.01f;
        if (s.c.holat == XV_FAVQULODDA) favq = 1;
    }
    TEKSHIR(favq && s.k.tezlik == 0 && tosiq - yol > 0.05f, "to'xtadi: oraliq %.2f m, v %.2f", tosiq - yol, s.k.tezlik);
    TEKSHIR(s.c.sabab & XV_S_ULTRATOVUSH, "sabab ultratovush");
    /* To'siq olib tashlansa 0,3 s dan keyin yurishga ruxsat */
    for (int j = 0; j < XV_OLDINGI_SONI; j++) s.k.ultratovush[j] = 0.2f;
    yur(&s, 0.05f, 5, 1);
    for (int j = 0; j < XV_OLDINGI_SONI; j++) s.k.ultratovush[j] = 4.5f;
    yur(&s, 0.2f, 5, 0);
    TEKSHIR(s.c.tezlik_max == 0, "darhol yurmaydi");
    yur(&s, 0.2f, 5, 0);
    TEKSHIR(s.c.tezlik_max > 0, "bo'shagach yuradi");
}

static void sinov_datchik_xatosi(void)
{
    Skuter s; yangi(&s);
    yur(&s, 4, 5, 1);
    s.k.ultratovush[1] = -1;
    yur(&s, 0.2f, 5, 1);
    TEKSHIR(s.c.tezlik_max > 4, "qisqa xato e'tiborsiz");
    yur(&s, 0.3f, 5, 1);
    TEKSHIR(s.c.tezlik_max <= 1.5f && (s.c.sabab & XV_S_DATCHIK_XATO), "uzoq xato: tezlik cheklanadi (%.2f)", s.c.tezlik_max);
}

static void sinov_jetson(void)
{
    Skuter s; yangi(&s);
    yur(&s, 4, 1, 1);
    yur(&s, 0.11f, 0, 1);
    TEKSHIR(s.c.holat == XV_NORMAL, "110 ms jim: hali normal");
    yur(&s, 0.03f, 0, 1);
    TEKSHIR(s.c.holat == XV_TOXTASH && s.c.tezlik_max == 0 && (s.c.sabab & XV_S_JETSON_KECH), "130 ms: yumshoq to'xtash");
    yur(&s, 1.0f, 0, 1);
    TEKSHIR(s.c.holat == XV_FAVQULODDA && (s.c.sabab & XV_S_JETSON_YOQ), "1,1 s: favqulodda");
    yur(&s, 0.1f, 5, 1);
    TEKSHIR(s.c.holat == XV_NORMAL && s.c.tezlik_max > 4, "Jetson qaytdi: davom");
}

static void sinov_operator(void)
{
    Skuter s; yangi(&s);
    yur(&s, 4, 5, 1);
    s.k.buyruq.operator_toxtat = true;
    yur(&s, 0.05f, 5, 1);
    s.k.buyruq.operator_toxtat = false;
    yur(&s, 0.5f, 5, 1);
    TEKSHIR(s.c.holat == XV_BLOKLANGAN && s.c.tezlik_max == 0, "to'xtatish bloklanadi");
    s.k.buyruq.operator_ochish = true;  /* hali to'xtamagan: ochilmaydi */
    yur(&s, 0.05f, 5, 1);
    TEKSHIR(s.c.holat == XV_BLOKLANGAN, "harakatda ochilmaydi (v=%.2f)", s.k.tezlik);
    yur(&s, 3, 5, 1);
    TEKSHIR(s.k.tezlik == 0, "to'xtadi");
    s.k.buyruq.operator_ochish = true;
    yur(&s, 0.05f, 5, 1);
    TEKSHIR(s.c.holat == XV_NORMAL && s.c.tezlik_max > 0, "to'xtagach operator ochdi");
    /* radio pult */
    s.k.radio_toxtat = true;
    yur(&s, 0.05f, 5, 1);
    s.k.radio_toxtat = false;
    yur(&s, 0.1f, 5, 1);
    TEKSHIR(s.c.holat == XV_BLOKLANGAN && (s.c.sabab & XV_S_RADIO), "radio pult");
}

static void sinov_motor_nosozligi(void)
{
    /* Oddiy sekin tormoz (1,2 m/s^2) bilan 5 m/s dan to'xtash - nosozlik emas */
    Skuter s; yangi(&s);
    yur(&s, 5, 5, 1);
    s.k.buyruq.tezlik = 0; s.k.buyruq.tormoz = 1.2f;
    for (int i = 0; i < 600; i++) {   /* motor buyruqqa 1,2 m/s^2 bilan bo'ysunadi */
        qadam(&s, i % 5 == 0, 0);
        s.k.tezlik = fmaxf(0.0f, s.k.tezlik - 1.2f * 0.01f);
    }
    TEKSHIR(!s.c.motor_uzish, "sekin tormoz nosozlik emas");
    /* Motor buyruqdan qochib ketdi: 2 m/s buyurilgan, 4 m/s yuryapti */
    yangi(&s);
    s.k.buyruq.tezlik = 2.0f;
    yur(&s, 3, 5, 1);
    s.k.tezlik = 4.0f;
    yur(&s, 0.4f, 5, 0);
    TEKSHIR(!s.c.motor_uzish, "0,4 s hali kutadi");
    yur(&s, 0.2f, 5, 0);
    TEKSHIR(s.c.motor_uzish && (s.c.sabab & XV_S_QOCHISH), "qochish: motor uziladi");
    s.k.tezlik = 0;
    yur(&s, 1, 5, 0);
    TEKSHIR(s.c.motor_uzish, "qayta yoqilguncha uzilgan");
}

static void sinov_batareya_qiyalik(void)
{
    Skuter s; yangi(&s);
    s.k.kuchlanish = 43.0f;
    yur(&s, 1, 5, 1);
    TEKSHIR(fabsf(s.c.tezlik_max - 8 * KMH) < 1e-3 && s.c.holat == XV_CHEKLANGAN, "kam batareya");
    s.k.kuchlanish = 40.0f;
    yur(&s, 0.1f, 5, 1);
    TEKSHIR(s.c.tezlik_max == 0 && s.c.holat == XV_TOXTASH, "kritik batareya");
    yangi(&s);
    yur(&s, 2, 5, 1);
    s.k.qiyalik = 30 * GRAD;
    yur(&s, 0.02f, 5, 1);
    TEKSHIR(s.c.motor_uzish && s.c.holat == XV_BLOKLANGAN, "yiqildi");
}

static void sinov_yon_gildirak(void)
{
    Skuter s; yangi(&s);
    s.k.buyruq.tezlik = 15 * KMH;
    yur(&s, 3.5f, 5, 1);   /* 12 km/soatga ~2,2 s da yetadi */
    TEKSHIR(s.h.yg == XV_YG_OCHIQ, "12 km/soatdan oshgach 2 s kutadi");
    yur(&s, 1.0f, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_YIGILMOQDA && s.c.yg_yigish_motor && s.c.yg_qulf, "yig'ilmoqda");
    yur(&s, 2.0f, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_YIGIQ && s.c.yg_qulf && !s.c.yg_yigish_motor, "yig'iq");
    /* 10 km/soat: gisterezis, yig'iq qoladi; 8 km/soat: ochiladi */
    s.k.buyruq.tezlik = 10 * KMH;
    yur(&s, 3, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_YIGIQ, "10 km/soatda yig'iq");
    s.k.buyruq.tezlik = 8 * KMH;
    yur(&s, 2, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_OCHIQ && !s.c.yg_qulf, "sekinlashdi: ochildi");
    /* Tok uzilsa qulf darhol bo'shaydi */
    yangi(&s);
    s.k.buyruq.tezlik = 15 * KMH;
    yur(&s, 7, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_YIGIQ, "yana yig'iq");
    s.k.tok_bor = false;
    yur(&s, 0.01f, 5, 1);
    TEKSHIR(!s.c.yg_qulf && s.h.yg == XV_YG_OCHILMOQDA, "tok yo'q: qulf bo'shadi");
    s.k.tok_bor = true;
    yur(&s, 5, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_OCHIQ, "xavfli sababdan keyin 10 s yig'ilmaydi");
    yur(&s, 9, 5, 1);
    TEKSHIR(s.h.yg != XV_YG_OCHIQ, "10 s dan keyin yana yig'iladi");
    /* Jetson kechiksa ochiladi */
    yur(&s, 3, 5, 1);
    yur(&s, 0.15f, 0, 1);
    TEKSHIR(s.h.yg == XV_YG_OCHILMOQDA || s.h.yg == XV_YG_OCHIQ, "Jetson kechikdi: ochildi");
    /* Ikki marta qiyalik: operator tekshirmaguncha yig'ilmaydi */
    yangi(&s);
    s.k.buyruq.tezlik = 15 * KMH;
    for (int n = 0; n < 2; n++) {
        yur(&s, 18, 5, 1);
        TEKSHIR(s.h.yg == XV_YG_YIGIQ, "%d: yig'iq", n);
        s.k.qiyalik = 9 * GRAD;
        yur(&s, 0.05f, 5, 1);
        s.k.qiyalik = 0;
    }
    yur(&s, 20, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_OCHIQ && s.h.yg_qulflangan, "2 qiyalik hodisasi: yig'ish o'chirildi");
    xv_yg_qulfni_ochish(&s.h);
    yur(&s, 4, 5, 1);
    TEKSHIR(s.h.yg != XV_YG_OCHIQ, "operator ochgach yig'iladi");
    /* Tez yo'l bo'lmasa yig'ilmaydi */
    yangi(&s);
    s.k.buyruq.tezlik = 15 * KMH; s.k.buyruq.tez_yol = false;
    yur(&s, 10, 5, 1);
    TEKSHIR(s.h.yg == XV_YG_OCHIQ, "trotuar/sekin yo'l: ochiq");
}

static void sinov_soat_aylanishi(void)
{
    Skuter s; yangi(&s);
    s.k.t_ms = UINT32_MAX - 2000;
    yur(&s, 4, 5, 1);   /* soat 0 dan o'tadi */
    TEKSHIR(s.c.holat == XV_NORMAL && s.k.tezlik > 4.9f, "millis() aylanishi");
}

static void sinov_protokol(void)
{
    uint8_t k[XP_MAX_KADR];
    XvBuyruq b = {.tezlik = -1.23f, .tormoz = 2.5f, .operator_toxtat = true, .tez_yol = true, .aloqa_bor = true}, o;
    XpParser p; xp_boshlash(&p);
    size_t n = xp_buyruq_yoz(7, &b, k);
    int ok = 0;
    for (size_t i = 0; i < n; i++) ok += xp_bayt(&p, k[i], &o);
    TEKSHIR(ok == 1 && fabsf(o.tezlik + 1.23f) < 1e-4 && fabsf(o.tormoz - 2.5f) < 1e-4 && o.operator_toxtat
            && !o.operator_ochish && o.tez_yol && o.aloqa_bor, "kodlash/o'qish");
    /* Takroriy seq */
    ok = 0;
    for (size_t i = 0; i < n; i++) ok += xp_bayt(&p, k[i], &o);
    TEKSHIR(ok == 0 && p.seq_xato == 1, "takroriy kadr rad etiladi");
    /* Buzilgan bayt */
    n = xp_buyruq_yoz(8, &b, k);
    k[6] ^= 0x10;
    ok = 0;
    for (size_t i = 0; i < n; i++) ok += xp_bayt(&p, k[i], &o);
    TEKSHIR(ok == 0 && p.crc_xato == 1, "CRC xato rad etiladi");
    /* Shovqin orasida 1000 kadr, seq 0..255 aylanadi */
    srand(1);
    xp_boshlash(&p);
    int qabul = 0, yuborildi = 0;
    for (int j = 0; j < 1000; j++) {
        int shovqin = rand() % 6;
        for (int i = 0; i < shovqin; i++) qabul += xp_bayt(&p, (uint8_t)(rand() % 256), &o);
        b.tezlik = (float)(j % 500) / 100.0f;
        n = xp_buyruq_yoz((uint8_t)j, &b, k);
        yuborildi++;
        int bu = 0;
        for (size_t i = 0; i < n; i++) bu += xp_bayt(&p, k[i], &o);
        if (bu) TEKSHIR(fabsf(o.tezlik - b.tezlik) < 1e-3, "qiymat to'g'ri");
        qabul += bu;
    }
    TEKSHIR(qabul >= 990 && qabul <= yuborildi, "shovqinda %d/%d kadr qabul qilindi", qabul, yuborildi);
    /* Holat kadri */
    XvChiqish c = {.tezlik_max = 3.3f, .holat = XV_FAVQULODDA, .sabab = XV_S_ULTRATOVUSH | XV_S_RADIO};
    n = xp_holat_yoz(1, &c, 2.5f, 49.87f, XV_YG_YIGIQ, k);
    TEKSHIR(n == 17 && k[3] == XP_TUR_HOLAT && k[5] == XV_FAVQULODDA && k[6] == 0x21 && k[12] == 0x7b && k[13] == 0x13,
            "holat kadri");
}

int main(void)
{
    sinov_oddiy();
    sinov_yoqilganda();
    sinov_ultratovush();
    sinov_datchik_xatosi();
    sinov_jetson();
    sinov_operator();
    sinov_motor_nosozligi();
    sinov_batareya_qiyalik();
    sinov_yon_gildirak();
    sinov_soat_aylanishi();
    sinov_protokol();
    printf("%d tekshiruv, %d xato\n", sinovlar, xatolar);
    return xatolar ? 1 : 0;
}
