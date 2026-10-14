#!/usr/bin/env bash
# Video oqimi bilan ishlash uchun yordamchi. Kompyuterda ffmpeg bo'lishi kerak.
#
#   ./oqim.sh sinov   SERVER PULT_PAROLI          sinov tasvirini serverga yuboradi (telefon o'rnida)
#   ./oqim.sh tekshir SERVER OPERATOR_PAROLI      serverga video kelyaptimi: kodek, o'lcham, kadr tezligi
#   ./oqim.sh rele    KIRISH SERVER PULT_PAROLI   boshqa manbadan serverga uzatadi, uzilsa qayta ulanadi.
#                                                 KIRISH: rtsp://..., http://... (MJPEG), tcp://... (xom oqim)
#                                                 yoki /dev/video0 (HDMI karta). Manzilni dron_qidiruv.py topadi.
#
# Sozlamalar (ixtiyoriy): YOL=dron, DAVOMIYLIK=60 (sinov, s), BITREYT=2500k, RTSP_TRANSPORT=tcp,
#   KIRISH_FORMAT=h264 (xom tcp:// oqim uchun ffmpeg formati, dron_qidiruv.py aytadi)
set -euo pipefail

YOL="${YOL:-dron}"
DAVOMIYLIK="${DAVOMIYLIK:-60}"
BITREYT="${BITREYT:-2500k}"
RTSP_TRANSPORT="${RTSP_TRANSPORT:-tcp}"
KIRISH_FORMAT="${KIRISH_FORMAT:-}"

yordam() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

srt_manzil() { echo "srt://$1:8890?streamid=publish:$YOL:pult:$2&pkt_size=1316"; }

# H.264, past kechikish, har 1 s da kalit kadr (ko'ruvchi tez ulanadi)
KODLASH=(-c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p
         -g 30 -keyint_min 30 -b:v "$BITREYT" -maxrate "$BITREYT" -bufsize "$BITREYT" -an)

sinov() {
  local server="${1:?server}" parol="${2:?pult paroli}"
  echo "Sinov tasviri ${DAVOMIYLIK} s yuboriladi. Ko'rish: http://$server:8889/$YOL"
  ffmpeg -hide_banner -loglevel warning -stats -re \
    -f lavfi -i "testsrc2=size=1280x720:rate=30" -t "$DAVOMIYLIK" \
    "${KODLASH[@]}" -f mpegts "$(srt_manzil "$server" "$parol")"
}

tekshir() {
  local server="${1:?server}" parol="${2:?operator paroli}"
  local url="rtsp://operator:$parol@$server:8554/$YOL"
  echo "== Oqim ($server, /$YOL) =="
  ffprobe -hide_banner -v error -rtsp_transport tcp -show_entries \
    stream=codec_type,codec_name,width,height,avg_frame_rate -of default=nw=1 "$url" || {
    echo "Oqim topilmadi. Pult yuboryaptimi, parol to'g'rimi, serverda 8554/tcp ochiqmi?" >&2
    exit 1
  }
  echo "== 10 s davomida qabul qilish =="
  local kadr
  kadr=$(ffmpeg -hide_banner -loglevel error -progress pipe:1 -rtsp_transport tcp -i "$url" \
           -t 10 -an -f null - | sed -n 's/^frame=//p' | tail -1)
  kadr="${kadr:-0}"
  echo "10 s videoda $kadr kadr (~$((kadr / 10)) kadr/s)."
  if (( kadr == 0 )); then
    echo "Kadr kelmadi: pult oqimni to'xtatgan yoki internet juda sekin." >&2
    exit 1
  fi
  echo "Video serverga yetib kelyapti."
}

rele() {
  local kirish="${1:?kirish}" server="${2:?server}" parol="${3:?pult paroli}"
  local manba
  case "$kirish" in
    rtsp://*)   manba=(-rtsp_transport "$RTSP_TRANSPORT" -i "$kirish" -c:v copy -an) ;;
    /dev/video*) manba=(-f v4l2 -framerate 30 -video_size 1280x720 -i "$kirish" "${KODLASH[@]}") ;;
    *)          manba=(${KIRISH_FORMAT:+-f "$KIRISH_FORMAT"} -i "$kirish" "${KODLASH[@]}") ;;
  esac
  while true; do
    ffmpeg -hide_banner -loglevel warning -stats "${manba[@]}" -f mpegts "$(srt_manzil "$server" "$parol")" || true
    echo "Oqim uzildi, 3 s dan keyin qayta ulanadi (to'xtatish: Ctrl+C)" >&2
    sleep 3
  done
}

case "${1:-}" in
  sinov)   shift; sinov "$@" ;;
  tekshir) shift; tekshir "$@" ;;
  rele)    shift; rele "$@" ;;
  *)       yordam ;;
esac
