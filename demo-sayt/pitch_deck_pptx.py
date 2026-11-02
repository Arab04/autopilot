from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image
import io, os

NAVY=RGBColor(0x0B,0x15,0x38); BLUE=RGBColor(0x24,0x57,0xFF); LIGHT=RGBColor(0xF6,0xF7,0xFB)
PALE=RGBColor(0x9D,0xB8,0xFF); ICE=RGBColor(0xDC,0xE6,0xFF); GRAY=RGBColor(0x4A,0x55,0x68)
MUTE=RGBColor(0x6A,0x71,0x79); WHITE=RGBColor(0xFF,0xFF,0xFF); LINE=RGBColor(0xDC,0xE0,0xEC); GREEN=RGBColor(0x1A,0x7F,0x3C); DEEP=RGBColor(0x2B,0x3A,0x67)
HEAD='Rubik'; BODY='Nunito Sans'
IMG='img/'  # demo-sayt.png va chirchiq-marshrutlar.png rasmlari ham shu papkada bo'lishi kerak

prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
blank=prs.slide_layouts[6]
# drop unused layouts to shrink the file
for lay in list(prs.slide_layouts):
    if lay is not blank:
        rId=prs.slide_master.part.relate_to(lay.part,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout')
        prs.slide_master.part.drop_rel(rId)
        sldLayoutIdLst=prs.slide_master._element.sldLayoutIdLst
        for lid in list(sldLayoutIdLst):
            if lid.rId==rId: sldLayoutIdLst.remove(lid)


def bg(slide,color):
    f=slide.background.fill; f.solid(); f.fore_color.rgb=color
def box(slide,x,y,w,h,fill=None,line=None,radius=True,lw=1):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    if radius: s.adjustments[0]=0.06
    if fill is None: s.fill.background()
    else: s.fill.solid(); s.fill.fore_color.rgb=fill
    if line is None: s.line.fill.background()
    else: s.line.color.rgb=line; s.line.width=Pt(lw)
    s.shadow.inherit=False
    return s
def text(slide,x,y,w,h,runs,anchor=MSO_ANCHOR.TOP,align=PP_ALIGN.LEFT):
    """runs: list of paragraphs; each paragraph = (text,size,color,bold,font) or list of such runs; or dict with 'bullet'"""
    tb=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=tb.text_frame; tf.word_wrap=True
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0; tf.vertical_anchor=anchor
    first=True
    for p in runs:
        para=tf.paragraphs[0] if first else tf.add_paragraph(); first=False; para.alignment=align
        space=None
        if isinstance(p,dict): space=p.get('space'); p=p['runs'] if 'runs' in p else [p['run']]
        elif isinstance(p,tuple): p=[p]
        for (t,size,color,bold,font) in p:
            r=para.add_run(); r.text=t; r.font.size=Pt(size); r.font.color.rgb=color; r.font.bold=bold; r.font.name=font
        if space is not None: para.space_before=Pt(space)
    return tb
def label(slide,x,y,t,color=BLUE,w=8):
    text(slide,x,y,w,0.35,[(t.upper(),11,color,True,BODY)])
def h2(slide,x,y,t,size=30,color=NAVY,w=11.3,h=1.3):
    text(slide,x,y,w,h,[(t,size,color,True,HEAD)])
def img(slide,path,x,y,w,h,maxpx=640,q=55,crop=True):
    im=Image.open(path).convert('RGB')
    if crop:
        tw,th=w,h; r=tw/th; W,H=im.size
        if W/H>r: nw=int(H*r); im=im.crop(((W-nw)//2,0,(W-nw)//2+nw,H))
        else: nh=int(W/r); im=im.crop((0,0,W,nh))
    im.thumbnail((maxpx,maxpx)); b=io.BytesIO(); im.save(b,'JPEG',quality=q,optimize=True); b.seek(0)
    pic=slide.shapes.add_picture(b,Inches(x),Inches(y),Inches(w),Inches(h)); return pic
def notes(slide,t): slide.notes_slide.notes_text_frame.text=t
def card(slide,x,y,w,h,parts,fill=WHITE,line=LINE,pad=0.25,top=None):
    box(slide,x,y,w,h,fill,line)
    if top: box(slide,x,y,w,0.08,top,None,radius=False)
    text(slide,x+pad,y+pad+(0.08 if top else 0),w-2*pad,h-2*pad,parts)
def table(slide,x,y,w,rows,colw,size=12,header=ICE,rowh=0.42,aligns=None):
    n=len(rows); m=len(rows[0])
    sh=slide.shapes.add_table(n,m,Inches(x),Inches(y),Inches(w),Inches(rowh*n)); tbl=sh.table
    tblPr=sh._element.graphic.graphicData.tbl.tblPr; tblPr.set('bandRow','0'); tblPr.set('firstRow','0')
    # remove style id for plain look
    for i,cw in enumerate(colw): tbl.columns[i].width=Inches(cw)
    for i,row in enumerate(rows):
        tbl.rows[i].height=Inches(rowh)
        for j,val in enumerate(row):
            c=tbl.cell(i,j); c.margin_left=c.margin_right=Inches(0.1); c.margin_top=c.margin_bottom=Inches(0.05)
            c.fill.solid(); c.fill.fore_color.rgb=header if (i==0 or (i==n-1 and val.startswith('**'))) else WHITE
            bold=i==0 or val.startswith('**'); color=NAVY
            if val.startswith('**'): val=val.strip('*')
            if val.startswith('@g'): val=val[2:]; color=GREEN
            tf=c.text_frame; tf.word_wrap=True; p=tf.paragraphs[0]; r=p.add_run(); r.text=val; r.font.size=Pt(size); r.font.bold=bold; r.font.color.rgb=color; r.font.name=BODY
            if aligns: p.alignment=aligns[j]
            c.vertical_anchor=MSO_ANCHOR.MIDDLE
    return tbl
def foot(slide,t,color=MUTE): text(slide,0.8,6.95,11.7,0.35,[(t,10,color,False,BODY)])
R=PP_ALIGN.RIGHT; L=PP_ALIGN.LEFT

# 1 cover
s=prs.slides.add_slide(blank); bg(s,NAVY)
label(s,0.8,0.9,'Pitch deck · 2026-yil noyabr',PALE)
text(s,0.8,1.35,10.5,2.6,[[('Toshkent ko‘chalarida ',46,LIGHT,True,HEAD),('o‘zi yuradigan',46,PALE,True,HEAD),(' yetkazib berish skuteri',46,LIGHT,True,HEAD)]])
text(s,0.8,4.6,10,1.0,[('Buyurtmani ombordan mijozgacha o‘zi olib boradi. Bitta operator 20 tagacha skuterni kuzatadi. Yetkazish kuryerdan 2–3 baravar arzon.',18,ICE,False,BODY)])
b=box(s,0.8,5.65,5.4,0.5,RGBColor(0x1E,0x2F,0x6B),RGBColor(0x5A,0x72,0xBF)); b.adjustments[0]=0.5
text(s,1.0,5.65,5.2,0.5,[('Sinovlar Chirchiq shahrida o‘tkazilmoqda',14,LIGHT,True,BODY)],anchor=MSO_ANCHOR.MIDDLE)
text(s,0.8,6.4,10,0.4,[('Isroil · Avtonom yetkazib berish skuterlari · Toshkent, O‘zbekiston',13,PALE,False,BODY)])
notes(s,'Salom, men Isroil. Biz Toshkent uchun o‘zi yuradigan yetkazib berish skuterini qurmoqdamiz; birinchi sinovlar Chirchiqda o‘tmoqda. Dastur simulyatsiyada tayyor, keyingi qadam haqiqiy skuter.')

# 2 muammo
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.7,'Muammo'); h2(s,0.8,1.05,'Yetkazib berish qimmat va kuryerga bog‘liq',34,h=0.8)
cards=[('$1,2–1,6','har bir yetkazish uchun kuryerga','Qisqa (2–6 km) buyurtmada bu narxning 30–50 foizi. Restoran va do‘konlar uchun eng katta xarajat.'),
('150 mln','yetkazish yiliga O‘zbekistonda','E-commerce yiliga 25–30% o‘smoqda. Kuryerlar yetishmaydi, tungi va yomg‘irli vaqtda narx yana oshadi.'),
('2 ta','kompaniya bozorni ushlab turibdi','Yandex Eats va Uzum Tezkor. Kichik biznes ularning komissiyasi va kuryer narxiga ko‘nishga majbur.')]
for i,(a,b_,c) in enumerate(cards):
    card(s,0.8+i*3.95,2.2,3.7,3.9,[(a,36,BLUE,True,HEAD),{'run':(b_,16,NAVY,True,BODY),'space':6},{'run':(c,13,GRAY,False,BODY),'space':8}])
foot(s,'Manbalar: davlat statistikasi (e-commerce $1,2 mlrd, 2024), Uzum 2025 hisoboti, Raqobat qo‘mitasi')
notes(s,'Kuryer narxi qisqa buyurtmaning yarmigacha yetadi. Bozor tez o‘smoqda, lekin ikki kompaniya nazoratida.')

# 3 yechim
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Yechim'); h2(s,0.8,0.95,'Yuk qutili elektr skuter o‘zi yuradi, operator faqat qiyin joyda yordam beradi',28,h=1.1)
steps=[('1 · Buyurtma','CRM yoki Telegram orqali tushadi. Dispetcher omborda turgan, zaryadi yetadigan skuterga beradi.'),
('2 · Yo‘lda','Yo‘l chetida, O‘zbekiston yo‘l qoidalari bo‘yicha: svetofor, yo‘l berish, to‘xtagan mashinani aylanib o‘tish.'),
('3 · Operator','Svetoforsiz katta chorrahada skuter to‘xtab ruxsat so‘raydi. Bitta operator 20 skuterga yetadi.'),
('4 · Topshirish','Mijoz Telegram botda kuzatadi, qutini PIN bilan ochadi. Skuter omborga qaytib zaryadlanadi.')]
for i,(a,b_) in enumerate(steps):
    card(s,0.8+i*2.95,2.3,2.75,2.5,[(a,15,BLUE,True,HEAD),{'run':(b_,12.5,GRAY,False,BODY),'space':6}],top=BLUE)
box(s,0.8,5.1,11.7,1.5,NAVY)
text(s,1.1,5.1,2.6,1.5,[('Nega hozir ishlaydi',20,PALE,True,HEAD)],anchor=MSO_ANCHOR.MIDDLE)
text(s,3.9,5.1,8.3,1.5,[('Faqat kamera (LiDAR shart emas), arzon Jetson kompyuter, bepul OpenStreetMap xaritasi va yarim avtonom rejim. Avtonomiya ulushi vaqt o‘tgan sari o‘sadi, operator soni emas.',13,ICE,False,BODY)],anchor=MSO_ANCHOR.MIDDLE)
notes(s,'Asosiy g‘oya: to‘liq avtonomiyani kutmaymiz. Skuter oddiy joylarda o‘zi yuradi, qiyin joyda odam yordam beradi. Shu tufayli hozir arzon va xavfsiz ishga tushadi.')

# 4 demo
s=prs.slides.add_slide(blank); bg(s,NAVY)
label(s,0.8,0.9,'Jonli demo',PALE); h2(s,0.8,1.3,'Chirchiqning haqiqiy xaritasida buyurtma bering va skuterni kuzating',28,LIGHT,w=6.6,h=1.8)
text(s,0.8,3.3,6.6,2.2,[{'run':('•  Ombor va 10 ta haqiqiy manzil, OpenStreetMap ko‘chalari',14,ICE,False,BODY)},{'run':('•  Skuter chorrahada ruxsat so‘raganda siz operator bo‘lasiz',14,ICE,False,BODY),'space':8},{'run':('•  O‘zbek, rus va ingliz tillarida, telefonda ham ishlaydi',14,ICE,False,BODY),'space':8}])
text(s,0.8,5.6,6.6,0.5,[('https://167-86-72-220.sslip.io/demo/',16,PALE,True,BODY)])
img(s,IMG+'demo-sayt.png',8.0,0.8,4.6,5.9,maxpx=400,q=45)
notes(s,'Demo saytni ochib ko‘rsating: buyurtma bering, skuter yo‘lga chiqadi, chorrahada ruxsat so‘raydi. Bu simulyatsiya, lekin xarita va marshrutlar haqiqiy.')

# 5 tayyor
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Nima tayyor'); h2(s,0.8,0.95,'Dastur $0 bilan yozildi va simulyatsiyada sinovdan o‘tdi',26,w=7.2,h=1.3)
stats=[('1 001 km','Chirchiq xaritasida yurildi, 0 ta to‘qnashuv'),('100 / 100','yetkazish 10 ta haqiqiy manzilga, 56% operatorsiz'),('14 / 14','xavfli ssenariy o‘tdi: avtobus, eshik, kamera o‘chishi'),('Serverda','operator paneli, flot, CRM, mijoz boti ishlab turibdi')]
for i,(a,b_) in enumerate(stats):
    card(s,0.8+(i%2)*3.65,2.5+(i//2)*1.85,3.45,1.65,[(a,26,BLUE,True,HEAD),{'run':(b_,12,GRAY,False,BODY),'space':4}],pad=0.22)
img(s,IMG+'chirchiq-marshrutlar.png',8.3,0.7,4.3,5.5,maxpx=380,q=45,crop=False)
text(s,8.3,6.3,4.3,0.4,[('Ombordan 10 manzilga marshrutlar, OpenStreetMap',11,MUTE,False,BODY)])
notes(s,'Hamma raqam simulyatsiyadan. Uskuna hali yig‘ilmagan, buni ochiq aytamiz. Lekin dastur qismi, odatda eng uzoq va qimmat qismi, tayyor.')

# 6 natijalar
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Operator paneli va flot'); h2(s,0.8,0.95,'20 ta skuterga 1 operator yetadi: buyurtmalarning 98 foizi 45 daqiqada',24,w=6.6,h=1.5)
table(s,0.8,2.6,6.6,[['Buyurtma / soat','Skuter','Operator','45 daqiqada'],['6','10','1','@g99%'],['12','20','1','@g98%'],['24','30','2','@g98%']],[2.1,1.5,1.5,1.5],aligns=[L,R,R,R])
text(s,0.8,4.6,6.6,1.2,[('10 soatlik ish kuni modeli, 3 ta tasodifiy kun o‘rtachasi. Operator vaqtining atigi 9% band, qolgan vaqtida boshqa ishni qilishi mumkin.',12.5,GRAY,False,BODY)])
img(s,IMG+'operator-panel.png',7.9,0.8,4.8,2.7,maxpx=420,q=40)
img(s,IMG+'flot-panel.png',7.9,3.7,4.8,2.7,maxpx=420,q=40)
foot(s,'Yuqorida: operator paneli (chorrahada ruxsat). Pastda: flot va dispetcherlik, buyurtmalar va PIN kodlar.')
notes(s,'Operator paneli serverda ishlab turibdi, uchrashuvda jonli ko‘rsatish mumkin. Flot modeli bizga nechta skuter va operator kerakligini aniq aytadi.')

# 7 bozor
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Bozor'); h2(s,0.8,0.95,'O‘zbekistonda «oxirgi mil» yetkazishga yiliga $200 mln+ sarflanadi',28,h=0.9)
mk=[('TAM · O‘zbekiston','$200–250 mln','yiliga kuryer xarajati hozir. 25–30% o‘sish bilan 2030 ga $500 mln+. E-commerce $1,2 mlrd (2024) → $1,8–2,2 mlrd (2027, KPMG).',NAVY,PALE,LIGHT,ICE,None),
('SAM · Skuter qila oladigan ish','$90–120 mln','6 km gacha, qutiga sig‘adigan shahar yetkazishlari (40–50%). Shundan Toshkent va viloyat ~60%.',BLUE,ICE,LIGHT,ICE,None),
('SOM · 5 yil','$12 mln / yil','Toshkent viloyatida 1 000 skuter, kuniga 30 yetkazish, $1,3 dan. Boshlanish: Chirchiq, 5 skuter, $0,3 mln bozor.',WHITE,BLUE,BLUE,GRAY,BLUE)]
for i,(a,b_,c,fill,lc,nc,tc,ln) in enumerate(mk):
    card(s,0.8+i*3.95,2.1,3.7,3.3,[(a.upper(),11,lc,True,BODY),{'run':(b_,30,nc,True,HEAD),'space':6},{'run':(c,12.5,tc,False,BODY),'space':8}],fill=fill,line=ln)
text(s,0.8,5.6,11.7,0.9,[('Qo‘shni bozor: Qozog‘iston O‘zbekistondan 5–6 baravar katta, Markaziy Osiyo bo‘yicha $1 mlrd+. Dunyo bo‘yicha yetkazuvchi robotlar bozori 2025: $0,8–1,1 mlrd, 2030: ~$3 mlrd.',13,GRAY,False,BODY)])
foot(s,'Hisob: ~150 mln yetkazish/yil × $1,2–1,6 kuryer haqi. Manbalar: davlat statistikasi, KPMG, Uzum 2025, ECDB, MarketsandMarkets.')
notes(s,'Bozor hajmi rasmiy hisobot emas, ochiq raqamlardan hisob. Kuryer soni va buyurtma soni bo‘yicha pastdan, GMV ulushi bo‘yicha yuqoridan hisoblaganda ikkalasi ham $200 mln atrofida chiqadi.')

# 8 iqtisod
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Biznes model'); h2(s,0.8,0.95,'Har bir yetkazishda kuryerdan 2–3 baravar arzon',30,h=0.8)
card(s,0.8,2.0,5.6,1.15,[('KURYER, BITTA YETKAZISH',10.5,MUTE,True,BODY),{'run':('$1,20–1,60',26,MUTE,True,HEAD),'space':2}],pad=0.2)
card(s,0.8,3.3,5.6,1.7,[('SKUTER, BITTA YETKAZISH (TANNARX)',10.5,PALE,True,BODY),{'run':('$0,40–0,60',26,PALE,True,HEAD),'space':2},{'run':('Skuter amortizatsiyasi ($8 ming / 3 yil), tok, 1 operator 20 skuterga, ta’mir va sug‘urta',11.5,ICE,False,BODY),'space':4}],fill=NAVY,line=None,pad=0.2)
card(s,0.8,5.15,5.6,1.5,[('NARXIMIZ HAMKORGA',10.5,BLUE,True,BODY),{'run':('$1,00',26,BLUE,True,HEAD),'space':2},{'run':('Hamkor 20–40% tejaydi, biz har yetkazishdan $0,40–0,60 marja olamiz',11.5,DEEP,False,BODY),'space':4}],fill=ICE,line=None,pad=0.2)
card(s,6.7,2.0,5.8,4.65,[('Kim to‘laydi',18,NAVY,True,HEAD),
 {'run':('•  Restoran, dorixona va do‘konlar: har yetkazish uchun to‘lov',12.5,GRAY,False,BODY),'space':8},
 {'run':('•  Yetkazish platformalari: bizning skuterlar ularning kuryer floti o‘rnida (B2B)',12.5,GRAY,False,BODY),'space':4},
 {'run':('•  Keyinroq: oylik obuna, 1 skuter = kuniga 25–30 yetkazish',12.5,GRAY,False,BODY),'space':4},
 {'run':('O‘z-o‘zini qoplash',18,NAVY,True,HEAD),'space':16},
 {'runs':[('Oylik xarajat ~$13 500 (jamoa, operatorlar, joy, aloqa). 20 skuter × 30 yetkazish × $1 × 30 kun = $18 000. ',12.5,GRAY,False,BODY),('20 skuterda break-even',12.5,NAVY,True,BODY),(', 5 skuterlik pilotda xarajatning ~40% qoplanadi.',12.5,GRAY,False,BODY)],'space':8}],pad=0.3)
foot(s,'Tannarx simulyatsiya natijalariga asoslangan taxmin; pilotda haqiqiy raqamlar o‘lchanadi.')
notes(s,'Asosiy raqam: tannarx $0,5 atrofida, kuryer $1,2 dan yuqori. Hamkorga $1 dan taklif qilsak ham, ikkala tomon yutadi. 20 skuterda loyiha o‘zini qoplaydi.')

# 9 raqobat
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.5,'Raqobat'); h2(s,0.8,0.85,'Yo‘lda yuradigan, arzon va mahalliy: shu uchlik bizda bor',28,h=0.8)
table(s,0.8,1.8,11.7,[['Kim','Qayerda yuradi','Narx / yetkazish','Bizning farqimiz'],
['Kuryerlar (Yandex, Uzum)','Yo‘l, mototsikl','$1,2–1,6','2–3 baravar arzon, kechasi va yomg‘irda narx oshmaydi, kuryer tanqisligi yo‘q'],
['Starship, Serve (AQSh, Yevropa)','Trotuar, 6 km/soat','$1–3','Yo‘lda 12–15 km/soat, 6–8 km radius; ularning roboti $5–10 ming, bizniki ~$3–5 ming'],
['Yandex Rover','Trotuar, faqat Rossiya','–','O‘zbekistonda yo‘q; Yandex xaritasi va qoidalari bizda mahalliy'],
['Dronlar','Havo','Yuqori','Shaharda ruxsat va xavfsizlik muammosi; biz mavjud yo‘l qoidalari ichida ishlaymiz']],[2.6,2.3,1.9,4.9],size=11.5,rowh=0.5)
him=[('Himoya 1 · Mahalliy ma’lumot','Chirchiq va Toshkent ko‘chalaridagi har bir km video va qaror bazamizni boyitadi.'),('Himoya 2 · Ruxsat va hamkorlar','Chirchiqda pilot uchun kelishuv bor; birinchi bo‘lib ishlagan hokimlik va YHXB bilan ishonch oladi.'),('Himoya 3 · Arzon uskuna','Faqat kamera, mahalliy skuter, ochiq kodli dastur: xorijiy robotdan 2–3 baravar arzon.')]
for i,(a,b_) in enumerate(him):
    card(s,0.8+i*3.95,4.9,3.7,1.75,[(a,14,NAVY,True,BODY),{'run':(b_,12,GRAY,False,BODY),'space':4}],top=BLUE,pad=0.22)
notes(s,'Xorijiy robotlar trotuarda sekin yuradi va qimmat. Biz yo‘lda, tezroq va arzonroq. Mahalliy ma’lumot va ruxsatlar vaqt o‘tishi bilan kuchli himoyaga aylanadi.')

# 10 reja
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.5,'Reja'); h2(s,0.8,0.85,'Pul tushgandan 4 oyda Chirchiqda haqiqiy mijozlar, 6 oyda pilot hisoboti',26,h=0.9)
cols=[('Bajarildi',['Muvozanat va yon g‘ildirak dasturi','Chirchiq xaritasi, 1 000 km simulyatsiya','Operator paneli serverda','Flot, CRM va mijoz boti'],NAVY,PALE,ICE,None),
('1-oy',['Qismlar buyurtmasi: skuter, kameralar, Jetson, xavfsizlik platasi','Birinchi skuterni yig‘ish, stendda sinov'],WHITE,BLUE,GRAY,BLUE),
('2-oy',['Birinchi skuter Chirchiq ko‘chasida, operator nazoratida','Maqsad: 500 km to‘qnashuvsiz'],WHITE,BLUE,GRAY,LINE),
('3–4-oy',['5 ta skuter, 1–2 hamkor restoran yoki do‘kon','Haqiqiy mijozlarga yetkazish boshlanadi'],WHITE,BLUE,GRAY,LINE),
('5–6-oy',['10 000+ yetkazish','Tannarx va ishonchlilik hisoboti','Keyingi raund: 100 skuter, $1,5–2 mln'],ICE,BLUE,DEEP,None)]
for i,(a,items,fill,lc,tc,ln) in enumerate(cols):
    parts=[(a.upper(),11,lc,True,BODY)]+[{'run':('•  '+t,11.5,tc,False,BODY),'space':5} for t in items]
    card(s,0.8+i*2.37,1.95,2.2,3.3,parts,fill=fill,line=ln,pad=0.2)
box(s,0.8,5.5,11.7,1.2,WHITE,LINE)
text(s,1.05,5.5,2.2,1.2,[('Asosiy xavflar',16,NAVY,True,HEAD)],anchor=MSO_ANCHOR.MIDDLE)
text(s,3.3,5.5,9.0,1.2,[('Qismlar yetib kelishi (Jetson, kameralar: 3–5 hafta, birinchi kundan buyurtma beramiz) · ruxsatlarni rasmiylashtirish (hokimlik va YHXB bilan ish boshlangan) · haqiqiy skuterga moslash (2–4 hafta zaxira qo‘yilgan).',12,GRAY,False,BODY)],anchor=MSO_ANCHOR.MIDDLE)
notes(s,'4 oy – maqsad, 6 oy – kafolat. Eng katta xavf qismlarning kechikishi, shuning uchun buyurtma birinchi kundan beriladi.')

# 11 jamoa
s=prs.slides.add_slide(blank); bg(s,LIGHT)
label(s,0.8,0.6,'Jamoa'); h2(s,0.8,0.95,'Kichik jamoa, tayyor dastur, Chirchiqda joyida ish',28,h=0.8)
team=[('Isroil','Asoschi, loyiha rahbari','[Tajribangiz: 2–3 jumla. Masalan: IT ta’lim markazi va CRM loyihalari, Chirchiqda hamkorlar va hokimlik bilan aloqa.]',NAVY,LIGHT,PALE,ICE,None),
('[Ism]','Robototexnika muhandisi','Skuterni yig‘ish, kameralar va sensorlar, avtonom yurish dasturini haqiqiy uskunaga moslash. [Ism yoki «qidirilmoqda»]',WHITE,NAVY,BLUE,GRAY,LINE),
('[Ism]','Kompyuter ko‘rish mutaxassisi','Odam, mashina, bordyurni aniqlash modellari, Chirchiq videolarida 99%+ aniqlik. [Ism yoki «qidirilmoqda»]',WHITE,NAVY,BLUE,GRAY,LINE),
('[Ism]','Backend dasturchi','Operator paneli, flot, CRM integratsiyasi va Telegram botlar. [Ism yoki «qidirilmoqda»]',WHITE,NAVY,BLUE,GRAY,LINE)]
for i,(a,b_,c,fill,nc,rc,tc,ln) in enumerate(team):
    card(s,0.8+i*2.95,2.0,2.75,3.2,[(a,20,nc,True,HEAD),{'run':(b_,12.5,rc,True,BODY),'space':4},{'run':(c,11.5,tc,False,BODY),'space':8}],fill=fill,line=ln,pad=0.22)
box(s,0.8,5.45,11.7,1.25,ICE)
text(s,1.05,5.45,2.0,1.25,[('Bugungacha',16,BLUE,True,HEAD)],anchor=MSO_ANCHOR.MIDDLE)
text(s,3.1,5.45,9.2,1.25,[('Dastur to‘liq simulyatsiyada yozildi va avtomatik sinovlardan o‘tadi (GitHub, har o‘zgarishda), operator paneli va flot tizimi serverda ishlab turibdi, Chirchiqda pilot uchun kelishuv bor. Hammasi tashqi mablag‘siz.',12,DEEP,False,BODY)],anchor=MSO_ANCHOR.MIDDLE)
notes(s,'Jamoa slaydida ismlar va tajribani o‘zingiz to‘ldiring. Agar hali yollanmagan bo‘lsa, «qidirilmoqda» deb yozing.')

# 12 sorov
s=prs.slides.add_slide(blank); bg(s,NAVY)
label(s,0.8,0.8,'So‘rov',PALE)
text(s,0.8,1.2,6.4,1.1,[('$300 000',48,LIGHT,True,HEAD)])
text(s,0.8,2.4,6.4,1.6,[('12 oyga, 10–15% ulush evaziga. 5 ta skuter Chirchiqdagi sinov hududida haqiqiy mijozlarga ishlaydi, keyin Toshkent, 10 000+ yetkazish, tannarx $0,6 dan past ekani isbotlanadi.',15,ICE,False,BODY)])
box(s,0.8,4.15,6.4,1.6,RGBColor(0x1E,0x2F,0x6B),RGBColor(0x5A,0x72,0xBF))
text(s,1.05,4.3,5.9,1.35,[('BOSQICHMA-BOSQICH BERISH MUMKIN',10.5,PALE,True,BODY),{'run':('$100 ming darhol (skuterlar yig‘iladi) · $100 ming birinchi skuter 500 km to‘qnashuvsiz yurgach · $100 ming 5 skuter mijozlarga ishlay boshlagach',12.5,ICE,False,BODY),'space':6}])
text(s,0.8,6.1,6.4,0.5,[('Aloqa: [telefon] · [email] · Demo: 167-86-72-220.sslip.io/demo',12.5,PALE,False,BODY)])
box(s,7.7,0.9,4.9,5.7,LIGHT,None)
text(s,8.0,1.15,4.3,0.5,[('Pul nimaga ketadi',18,NAVY,True,HEAD)])
table(s,8.0,1.75,4.3,[['Modda','USD'],['5 ta skuter va ehtiyot qismlar','65 000'],['4 kishilik jamoa, 12 oy','110 000'],['Operatorlar va dala texnigi','25 000'],['Ruxsat, sug‘urta, sertifikat','15 000'],['Operator markazi, joy, internet','12 000'],['Hamkorlar va marketing','8 000'],['Zaxira (20%)','65 000'],['**Jami','**300 000']],[3.1,1.2],size=11.5,rowh=0.46,aligns=[L,R])
notes(s,'$300 ming, 12 oy, 10–15% ulush. Investor xavfini kamaytirish uchun uch bosqichda berish mumkin. Aloqa ma’lumotlarini to‘ldiring.')

out='pitch-deck.pptx'
prs.save(out); print(os.path.getsize(out))
