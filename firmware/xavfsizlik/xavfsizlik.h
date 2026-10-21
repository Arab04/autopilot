/*
 * Xavfsizlik platasi (mikrokontroller) mantig'i: skuterning oxirgi himoya qatlami.
 *
 * Asosiy kompyuter (Jetson) nima buyursa ham, bu dastur quyidagilarni o'zi tekshiradi:
 *   - oldinda ultratovush juda yaqin narsa ko'rsa: favqulodda tormoz;
 *   - Jetson 120 ms javob bermasa: yumshoq to'xtash, 1 s bermasa: favqulodda;
 *   - operator yoki radio pult "to'xta" desa: favqulodda, faqat skuter to'xtagach operator ochadi;
 *   - tezlik chegarasi (20 km/soat), motor buyruqdan oshib ketsa (nosozlik): tokni uzish;
 *   - qiyalik va batareya;
 *   - yon g'ildiraklar (docs: yon-gildirak-mexanizm.md, 5-bo'lim).
 *
 * Apparatga bog'liq emas: har 10 ms da xv_qadam() chaqiriladi, kirish va chiqish oddiy struct.
 * Shuning uchun kompyuterda sinaladi (test_xavfsizlik.c) va Python simulyatoriga ulanadi (ctypes).
 */
#ifndef XAVFSIZLIK_H
#define XAVFSIZLIK_H

#include <stdbool.h>
#include <stdint.h>

#define XV_ULTRATOVUSH_SONI 8   /* 0..2 oldinga qaragan, qolganlari yon va orqa */
#define XV_OLDINGI_SONI 3

typedef struct {
    float max_tezlik;          /* m/s, har qanday holatda (20 km/soat) */
    float reaksiya;            /* s, tormoz boshlanguncha */
    float favqulodda_tormoz;   /* m/s^2 */
    float yumshoq_tormoz;      /* m/s^2 */
    float ultratovush_zaxira;  /* m, to'xtash yo'liga qo'shiladi */
    float ultratovush_bosh_vaqt; /* s, to'siq yo'qolgach shuncha kutib keyin yurishga ruxsat */
    float datchik_xato_vaqt;   /* s, oldingi datchik shuncha xato bersa tezlik cheklanadi */
    float datchik_xato_tezlik; /* m/s */
    uint32_t jetson_kechikish_ms;  /* shundan keyin "dastur xatosi": yumshoq to'xtash */
    uint32_t jetson_uzilish_ms;    /* shundan keyin favqulodda */
    float qochish_farq;        /* m/s, tezlik buyruqdan shuncha oshsa */
    float qochish_vaqt;        /* s, va shuncha davom etsa: motor uziladi */
    float yiqilish_qiyalik;    /* rad, bundan oshsa motor uziladi */
    float kam_kuchlanish;      /* V, tezlik cheklanadi */
    float kam_kuchlanish_tezlik; /* m/s */
    float kritik_kuchlanish;   /* V, to'xtash */
    /* Yon g'ildiraklar */
    float yigish_tezlik;       /* m/s (12 km/soat) */
    float yigish_ushlab;       /* s */
    float yigish_max_qiyalik;  /* rad (3 grad) */
    float ochish_tezlik;       /* m/s (9 km/soat) */
    float ochish_qiyalik;      /* rad (8 grad) */
    float keskin_tormoz;       /* m/s^2, buyurilgan tormoz bundan katta bo'lsa ochiladi */
    float ochilgach_kutish;    /* s, xavfli sabab bilan ochilgandan keyin yig'ilmaydi */
    uint8_t max_qiyalik_hodisa; /* shuncha marta qiyalik sabab ochilsa, yig'ish o'chiriladi */
    float ultratovush_masofa;  /* m, datchikning eng uzoq masofasi: shundan uzoq = oldinda hech narsa yo'q */
} XvSozlama;

void xv_standart_sozlama(XvSozlama *s);

/* Jetson buyrug'i (protokol.h orqali keladi) */
typedef struct {
    float tezlik;              /* m/s, rejalovchi xohlagan tezlik */
    float tormoz;              /* m/s^2, rejalovchi ruxsat bergan sekinlashish */
    bool operator_toxtat;      /* operator panelidagi favqulodda tugma */
    bool operator_ochish;      /* operator to'xtatishni bekor qildi */
    bool tez_yol;              /* marshrutning bu qismida tez yurish mumkin (yon g'ildirakni yig'ish uchun) */
    bool aloqa_bor;            /* 4G aloqa bor */
} XvBuyruq;

typedef struct {
    uint32_t t_ms;             /* plata soati */
    float tezlik;              /* m/s, g'ildirak datchigidan (Jetsondan emas) */
    float ultratovush[XV_ULTRATOVUSH_SONI]; /* m; manfiy = datchik javob bermadi;
                                  >= ultratovush_masofa = aks-sado qaytmadi (oldinda bo'sh) */
    float qiyalik;             /* rad, platadagi o'z IMU si; + o'ngga */
    float kuchlanish;          /* V, batareya */
    bool tok_bor;              /* yon g'ildirak qulfi uchun 12 V bor */
    bool radio_toxtat;         /* qo'ldagi radio pult tugmasi (bevosita platada) */
    bool buyruq_yangi;         /* shu qadamda Jetsondan to'g'ri (CRC li) kadr keldi */
    XvBuyruq buyruq;           /* buyruq_yangi bo'lsa yangi qiymat */
} XvKirish;

typedef enum {
    XV_NORMAL = 0,
    XV_CHEKLANGAN,      /* yurish mumkin, lekin tezlik cheklangan (datchik xatosi, batareya) */
    XV_TOXTASH,         /* yumshoq to'xtash (Jetson kechikdi) */
    XV_FAVQULODDA,      /* favqulodda tormoz */
    XV_BLOKLANGAN       /* to'xtatilgan, operator ochishi kerak */
} XvHolatTuri;

/* Sabablar (bitlar), status kadrida Jetsonga va operator paneliga yuboriladi */
enum {
    XV_S_ULTRATOVUSH  = 1u << 0,
    XV_S_DATCHIK_XATO = 1u << 1,
    XV_S_JETSON_KECH  = 1u << 2,
    XV_S_JETSON_YOQ   = 1u << 3,
    XV_S_OPERATOR     = 1u << 4,
    XV_S_RADIO        = 1u << 5,
    XV_S_QOCHISH      = 1u << 6,
    XV_S_YIQILISH     = 1u << 7,
    XV_S_BATAREYA     = 1u << 8,
    XV_S_KRITIK_BATAREYA = 1u << 9,
    XV_S_TEZLIK_CHEGARA = 1u << 10,
};

typedef enum { XV_YG_OCHIQ = 0, XV_YG_YIGILMOQDA, XV_YG_YIGIQ, XV_YG_OCHILMOQDA } XvYonGildirak;

typedef struct {
    float tezlik_max;          /* motor kontrolleriga: bundan tez yurma */
    float tormoz;              /* m/s^2: 0 = mexanik tormoz kerak emas */
    bool motor_uzish;          /* motor tokini butunlay uzish (nosozlik) */
    bool yg_qulf;              /* yon g'ildirak elektromagnit qulfi: true = yig'iq ushlab tur */
    bool yg_yigish_motor;      /* yig'ish motorini aylantir */
    bool signal;               /* ovoz/chiroq */
    XvHolatTuri holat;
    uint32_t sabab;
} XvChiqish;

typedef struct {
    XvSozlama s;
    bool boshlangan;
    uint32_t oxirgi_t_ms;
    uint32_t oxirgi_buyruq_ms;
    bool buyruq_bor;
    XvBuyruq buyruq;
    /* ultratovush */
    bool ut_tormoz;
    float ut_bosh_vaqt;        /* oldinda bo'sh bo'lganiga necha s */
    float datchik_xato_vaqt;
    /* favqulodda blok */
    bool bloklangan;
    uint32_t blok_sabab;
    /* motor nosozligi */
    float qochish_vaqt;
    float v_kutilgan;          /* buyruq va ruxsat etilgan sekinlashishdan kutilgan tezlik */
    bool motor_nosoz;          /* faqat plata qayta yoqilganda tiklanadi */
    /* yon g'ildirak */
    XvYonGildirak yg;
    float yg_pos;              /* 1 = ochiq, 0 = yig'iq (yig'ish motori vaqtidan baholanadi) */
    float tez_vaqt;            /* tezlik chegaradan yuqorida necha s */
    float yg_kutish;           /* xavfli ochilishdan keyin qolgan kutish (s) */
    uint8_t qiyalik_hodisa;
    bool yg_qulflangan;        /* operator tekshirmaguncha yig'ilmaydi */
} XvHolat;

void xv_boshlash(XvHolat *h, const XvSozlama *s);
void xv_qadam(XvHolat *h, const XvKirish *k, XvChiqish *c);
/* Operator ustaxonada tekshirgach: yon g'ildirak yig'ish qulfini ochish */
void xv_yg_qulfni_ochish(XvHolat *h);
/* Boshqa tillardan (ctypes) chaqirganda xotira ajratish uchun */
unsigned xv_holat_hajmi(void);

#endif
