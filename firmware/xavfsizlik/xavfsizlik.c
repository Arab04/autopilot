#include "xavfsizlik.h"

#include <math.h>
#include <string.h>

#define KMH (1.0f / 3.6f)
#define GRAD (3.14159265f / 180.0f)
#define YG_OCHILISH_S 0.3f   /* prujina bilan ochilish vaqti */
#define YG_YIGILISH_S 1.5f   /* motor bilan yig'ish vaqti */

void xv_standart_sozlama(XvSozlama *s)
{
    /* Qiymatlar Python simulyatoridagi bilan bir xil (autopilot/haydash.py, autopilot/yol.py,
     * sim/balance/skuter_sim.py), shunda simulyatsiya natijalari platadagi dasturga ham tegishli. */
    s->max_tezlik = 20 * KMH;
    s->reaksiya = 0.15f;
    s->favqulodda_tormoz = 4.0f;
    s->yumshoq_tormoz = 2.5f;
    s->ultratovush_zaxira = 0.3f;
    s->ultratovush_bosh_vaqt = 0.3f;
    s->datchik_xato_vaqt = 0.3f;
    s->datchik_xato_tezlik = 1.5f;
    s->jetson_kechikish_ms = 120;
    s->jetson_uzilish_ms = 1000;
    s->qochish_farq = 1.5f;
    s->qochish_vaqt = 0.5f;
    s->yiqilish_qiyalik = 25 * GRAD;
    s->kam_kuchlanish = 44.0f;      /* 48 V batareya (13S): ~10% qolganda */
    s->kam_kuchlanish_tezlik = 8 * KMH;
    s->kritik_kuchlanish = 41.0f;
    s->yigish_tezlik = 12 * KMH;
    s->yigish_ushlab = 2.0f;
    s->yigish_max_qiyalik = 3 * GRAD;
    s->ochish_tezlik = 9 * KMH;
    s->ochish_qiyalik = 8 * GRAD;
    s->keskin_tormoz = 3.0f;
    s->ochilgach_kutish = 10.0f;
    s->max_qiyalik_hodisa = 2;
    s->ultratovush_masofa = 4.5f;   /* JSN-SR04T */
}

void xv_boshlash(XvHolat *h, const XvSozlama *s)
{
    memset(h, 0, sizeof(*h));
    h->s = *s;
    h->yg = XV_YG_OCHIQ;   /* yoqilganda yon g'ildiraklar doim ochiq */
    h->yg_pos = 1.0f;
}

void xv_yg_qulfni_ochish(XvHolat *h)
{
    h->yg_qulflangan = false;
    h->qiyalik_hodisa = 0;
}

unsigned xv_holat_hajmi(void) { return (unsigned)sizeof(XvHolat); }

static float minf(float a, float b) { return a < b ? a : b; }
static float maxf(float a, float b) { return a > b ? a : b; }

static void yon_gildirak(XvHolat *h, const XvKirish *k, float dt, bool sog, bool xavf, XvChiqish *c)
{
    const XvSozlama *s = &h->s;
    float v = k->tezlik, q = fabsf(k->qiyalik);
    bool yol_ok = h->buyruq_bor && h->buyruq.tez_yol && h->buyruq.aloqa_bor;
    bool qiyalik_katta = q > s->ochish_qiyalik;
    bool ochish_kerak = !k->tok_bor || !sog || xavf || qiyalik_katta || v < s->ochish_tezlik || !yol_ok;

    if (h->yg_kutish > 0) h->yg_kutish = maxf(0.0f, h->yg_kutish - dt);
    if (ochish_kerak && (h->yg == XV_YG_YIGIQ || h->yg == XV_YG_YIGILMOQDA)) {
        h->yg = XV_YG_OCHILMOQDA;
        /* Oddiy sekinlashish xavfli emas; qolganlari - yig'ish biroz kutadi */
        if (!k->tok_bor || !sog || xavf || qiyalik_katta) h->yg_kutish = s->ochilgach_kutish;
        if (qiyalik_katta && ++h->qiyalik_hodisa >= s->max_qiyalik_hodisa) h->yg_qulflangan = true;
    }
    if (v > s->yigish_tezlik && !ochish_kerak) h->tez_vaqt += dt;
    else h->tez_vaqt = 0;
    if (h->yg == XV_YG_OCHIQ && h->tez_vaqt >= s->yigish_ushlab && q < s->yigish_max_qiyalik
        && h->yg_kutish <= 0 && !h->yg_qulflangan) {
        h->yg = XV_YG_YIGILMOQDA;
    }
    if (h->yg == XV_YG_OCHILMOQDA) {
        h->yg_pos = minf(1.0f, h->yg_pos + dt / YG_OCHILISH_S);
        if (h->yg_pos >= 1.0f) h->yg = XV_YG_OCHIQ;
    } else if (h->yg == XV_YG_YIGILMOQDA) {
        h->yg_pos = maxf(0.0f, h->yg_pos - dt / YG_YIGILISH_S);
        if (h->yg_pos <= 0.0f) h->yg = XV_YG_YIGIQ;
    }
    /* Qulf tok bilan ushlab turadi: tok yo'qolsa prujina o'zi ochadi */
    c->yg_qulf = k->tok_bor && (h->yg == XV_YG_YIGIQ || h->yg == XV_YG_YIGILMOQDA);
    c->yg_yigish_motor = k->tok_bor && h->yg == XV_YG_YIGILMOQDA;
}

void xv_qadam(XvHolat *h, const XvKirish *k, XvChiqish *c)
{
    const XvSozlama *s = &h->s;
    float dt = 0.0f;
    if (h->boshlangan) dt = (float)(uint32_t)(k->t_ms - h->oxirgi_t_ms) / 1000.0f;
    if (dt > 0.1f) dt = 0.1f;   /* sikl kechiksa ham hisob sakrab ketmasin */
    h->boshlangan = true;
    h->oxirgi_t_ms = k->t_ms;

    if (k->buyruq_yangi) {
        h->buyruq = k->buyruq;
        h->oxirgi_buyruq_ms = k->t_ms;
        h->buyruq_bor = true;
    }
    float v = k->tezlik;
    uint32_t sabab = 0;
    float tezlik_max = s->max_tezlik, tormoz = 0.0f;
    XvHolatTuri holat = XV_NORMAL;

    /* 1. Operator va radio pult: to'xtatish bloklanadi, faqat to'xtagan skuterda operator ochadi */
    if (k->buyruq_yangi && k->buyruq.operator_toxtat) { h->bloklangan = true; h->blok_sabab |= XV_S_OPERATOR; }
    if (k->radio_toxtat) { h->bloklangan = true; h->blok_sabab |= XV_S_RADIO; }
    if (h->bloklangan && k->buyruq_yangi && k->buyruq.operator_ochish && !k->buyruq.operator_toxtat
        && !k->radio_toxtat && fabsf(v) < 0.05f) {
        h->bloklangan = false;
        h->blok_sabab = 0;
    }

    /* 2. Yiqilish */
    if (fabsf(k->qiyalik) > s->yiqilish_qiyalik) { h->bloklangan = true; h->blok_sabab |= XV_S_YIQILISH; }

    /* 3. Jetson */
    uint32_t yosh = h->buyruq_bor ? (uint32_t)(k->t_ms - h->oxirgi_buyruq_ms) : UINT32_MAX;
    bool jetson_sog = yosh <= s->jetson_kechikish_ms;
    if (h->buyruq_bor && jetson_sog) {
        tezlik_max = minf(tezlik_max, maxf(0.0f, h->buyruq.tezlik));
        tormoz = maxf(0.0f, h->buyruq.tormoz);
    }
    if (yosh > s->jetson_uzilish_ms) {
        sabab |= XV_S_JETSON_YOQ;
        tezlik_max = 0; tormoz = s->favqulodda_tormoz;
        holat = XV_FAVQULODDA;
    } else if (!jetson_sog) {
        sabab |= XV_S_JETSON_KECH;
        tezlik_max = 0; tormoz = maxf(tormoz, s->yumshoq_tormoz);
        if (holat < XV_TOXTASH) holat = XV_TOXTASH;
    }

    /* 4. Batareya */
    if (k->kuchlanish < s->kritik_kuchlanish) {
        sabab |= XV_S_KRITIK_BATAREYA;
        tezlik_max = 0; tormoz = maxf(tormoz, s->yumshoq_tormoz);
        if (holat < XV_TOXTASH) holat = XV_TOXTASH;
    } else if (k->kuchlanish < s->kam_kuchlanish) {
        sabab |= XV_S_BATAREYA;
        tezlik_max = minf(tezlik_max, s->kam_kuchlanish_tezlik);
        if (holat < XV_CHEKLANGAN) holat = XV_CHEKLANGAN;
    }

    /* 5. Oldingi ultratovush datchiklari */
    float d = INFINITY;
    bool xato = false;
    for (int i = 0; i < XV_OLDINGI_SONI; i++) {
        if (k->ultratovush[i] < 0) xato = true;
        else if (k->ultratovush[i] < s->ultratovush_masofa) d = minf(d, k->ultratovush[i]);
    }
    h->datchik_xato_vaqt = xato ? h->datchik_xato_vaqt + dt : 0.0f;
    if (h->datchik_xato_vaqt > s->datchik_xato_vaqt) {
        sabab |= XV_S_DATCHIK_XATO;
        tezlik_max = minf(tezlik_max, s->datchik_xato_tezlik);
        if (holat < XV_CHEKLANGAN) holat = XV_CHEKLANGAN;
    }
    float vp = maxf(v, 0.0f);
    float toxtash_yoli = vp * s->reaksiya + vp * vp / (2 * s->favqulodda_tormoz) + s->ultratovush_zaxira;
    if (d < toxtash_yoli) {
        h->ut_tormoz = true;
        h->ut_bosh_vaqt = 0;
    } else if (h->ut_tormoz) {
        h->ut_bosh_vaqt += dt;
        if (h->ut_bosh_vaqt >= s->ultratovush_bosh_vaqt) h->ut_tormoz = false;
    }
    if (h->ut_tormoz) {
        sabab |= XV_S_ULTRATOVUSH;
        tezlik_max = 0; tormoz = s->favqulodda_tormoz;
        holat = XV_FAVQULODDA;
    }

    /* 6. Motor buyruqdan oshib ketdi (kontroller yoki dastur nosozligi): tokni uzish, qayta yoqilguncha */
    if (v > s->max_tezlik + 0.5f) sabab |= XV_S_TEZLIK_CHEGARA;
    /* Kutilgan tezlik: Jetson buyrug'i, buyruq kamayganda esa ruxsat etilgan tormoz bilan pasayib boradi
     * (tormozlash paytida buyruqdan tezroq bo'lish normal). Haqiqiy tezlik undan sezilarli oshsa - nosozlik. */
    float ruxsat = (h->buyruq_bor && jetson_sog) ? maxf(0.0f, minf(h->buyruq.tezlik, s->max_tezlik)) : 0.0f;
    float sekinlash = 0.7f * maxf(0.5f, h->buyruq.tormoz > 0 ? minf(h->buyruq.tormoz, s->favqulodda_tormoz)
                                                               : s->yumshoq_tormoz);
    h->v_kutilgan = maxf(ruxsat, h->v_kutilgan - sekinlash * dt);
    h->qochish_vaqt = v > h->v_kutilgan + s->qochish_farq ? h->qochish_vaqt + dt : 0.0f;
    if (h->qochish_vaqt > s->qochish_vaqt) h->motor_nosoz = true;
    if (h->motor_nosoz) {
        sabab |= XV_S_QOCHISH;
        tezlik_max = 0; tormoz = s->favqulodda_tormoz;
        holat = XV_FAVQULODDA;
    }

    if (h->bloklangan) {
        sabab |= h->blok_sabab;
        tezlik_max = 0; tormoz = s->favqulodda_tormoz;
        holat = XV_BLOKLANGAN;
    }

    bool sog = jetson_sog && !h->motor_nosoz && !(sabab & XV_S_DATCHIK_XATO);
    bool xavf = h->ut_tormoz || h->bloklangan || tormoz >= s->keskin_tormoz;
    yon_gildirak(h, k, dt, sog, xavf, c);

    c->tezlik_max = tezlik_max;
    c->tormoz = v > tezlik_max ? maxf(tormoz, 0.5f) : (tezlik_max == 0 ? tormoz : 0.0f);
    c->motor_uzish = h->motor_nosoz || (h->blok_sabab & XV_S_YIQILISH);
    c->holat = holat;
    c->sabab = sabab;
    c->signal = holat >= XV_TOXTASH;
}
