import csv
import io
import os
import socket
import threading
import time

import qrcode
import qrcode.image.svg
from flask import Flask, Response, abort, jsonify, render_template, request
from flask_socketio import SocketIO, emit, join_room
from werkzeug.middleware.proxy_fix import ProxyFix

from game import GameError, Oturum

KOK = os.path.dirname(os.path.abspath(__file__))


def klasor(ad):
    yol = os.path.join(KOK, ad)
    return yol if os.path.isdir(yol) else KOK


app = Flask(__name__, template_folder=klasor("templates"), static_folder=klasor("static"), static_url_path="/static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(24).hex()
socketio = SocketIO(app, async_mode="threading")

SURUM = str(int(time.time()))


@app.context_processor
def surum_ekle():
    return {"surum": SURUM}


KILIT = threading.RLock()
OTURUMLAR = {}
BAGLANTILAR = {}
OYUNCU_SID = {}


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def taban_adres():
    taban = os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if taban:
        return taban.rstrip("/")
    host, _, port = request.host.partition(":")
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        host = lan_ip()
    varsayilan = (request.scheme == "http" and port in ("", "80")) or (request.scheme == "https" and port in ("", "443"))
    return f"{request.scheme}://{host}" + ("" if varsayilan else f":{port}")


def katilim_adresi(pin):
    return f"{taban_adres()}/j/{pin}"


def oturum_al(pin):
    o = OTURUMLAR.get(str(pin))
    if not o:
        raise GameError("Bu PIN ile aktif bir oturum yok.")
    return o


def yayinla(o):
    simdi = time.time()
    socketio.emit("durum", o.host_gorunum(simdi), to=f"host:{o.pin}")
    for pid, sid in list(OYUNCU_SID.get(o.pin, {}).items()):
        socketio.emit("durum", o.oyuncu_gorunum(pid, simdi), to=sid)


def sayac_dongusu():
    while True:
        socketio.sleep(0.25)
        with KILIT:
            for o in list(OTURUMLAR.values()):
                try:
                    if o.tik():
                        yayinla(o)
                except GameError:
                    pass
            eski = [p for p, o in OTURUMLAR.items() if time.time() - o.olusturma > 6 * 3600]
            for p in eski:
                OTURUMLAR.pop(p, None)
                OYUNCU_SID.pop(p, None)


@app.route("/yonetici")
def host_sayfa():
    return render_template("host.html")


@app.route("/")
@app.route("/j/<pin>")
@app.route("/j/")
def oyuncu_sayfa(pin=""):
    return render_template("player.html", pin=pin)


@app.post("/api/oturum")
def oturum_olustur():
    with KILIT:
        o = Oturum()
        while o.pin in OTURUMLAR:
            o = Oturum()
        OTURUMLAR[o.pin] = o
        return jsonify({"pin": o.pin, "token": o.host_token, "katilim": katilim_adresi(o.pin), "kisa": taban_adres().split("://", 1)[-1]})


@app.get("/api/oturum/<pin>/adres")
def adres(pin):
    if pin not in OTURUMLAR:
        abort(404)
    return jsonify({"katilim": katilim_adresi(pin), "kisa": taban_adres().split("://", 1)[-1]})


@app.get("/qr/<pin>.svg")
def qr(pin):
    if pin not in OTURUMLAR:
        abort(404)
    img = qrcode.make(katilim_adresi(pin), image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), mimetype="image/svg+xml")


@app.get("/disa-aktar/<pin>.csv")
def disa_aktar(pin):
    o = OTURUMLAR.get(pin)
    if not o or request.args.get("token") != o.host_token:
        abort(403)
    buf = io.StringIO()
    csv.writer(buf, delimiter=";").writerows(o.disa_aktar_satirlar())
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=prizma-{pin}.csv"})


@socketio.on("host:merhaba")
def host_merhaba(veri):
    with KILIT:
        try:
            o = oturum_al(veri.get("pin"))
        except GameError as e:
            return {"ok": False, "hata": str(e)}
        if veri.get("token") != o.host_token:
            return {"ok": False, "hata": "Yönetici anahtarı geçersiz."}
        join_room(f"host:{o.pin}")
        BAGLANTILAR[request.sid] = ("host", o.pin, None)
        emit("durum", o.host_gorunum())
        return {"ok": True}


HOST_EYLEMLERI = {
    "takim_kur": lambda o, d: o.takim_kur(),
    "karistir": lambda o, d: o.takim_kur(),
    "lobiye_don": lambda o, d: o.lobiye_don(),
    "onay": lambda o, d: o.onay(d.get("item"), bool(d.get("deger"))),
    "hepsini_onayla": lambda o, d: o.hepsini_onayla(),
    "ek": lambda o, d: o.ek(d.get("item"), bool(d.get("deger"))),
    "kisa": lambda o, d: o.kisa(bool(d.get("deger"))),
    "baslat": lambda o, d: o.baslat(),
    "ilerle": lambda o, d: o.ilerle(),
    "cikar": lambda o, d: o.oyuncu_cikar(d.get("oyuncu")),
}


@socketio.on("host:eylem")
def host_eylem(veri):
    with KILIT:
        bag = BAGLANTILAR.get(request.sid)
        if not bag or bag[0] != "host":
            return {"ok": False, "hata": "Yönetici oturumu doğrulanmadı."}
        o = OTURUMLAR.get(bag[1])
        islem = HOST_EYLEMLERI.get(veri.get("eylem"))
        if not o or not islem:
            return {"ok": False, "hata": "Geçersiz işlem."}
        try:
            islem(o, veri.get("veri") or {})
        except GameError as e:
            return {"ok": False, "hata": str(e)}
        yayinla(o)
        return {"ok": True}


def oyuncu_bagla(o, p):
    eski = OYUNCU_SID.setdefault(o.pin, {}).get(p["id"])
    if eski and eski != request.sid:
        BAGLANTILAR.pop(eski, None)
        socketio.emit("baska_cihaz", {}, to=eski)
    OYUNCU_SID[o.pin][p["id"]] = request.sid
    BAGLANTILAR[request.sid] = ("oyuncu", o.pin, p["id"])
    o.baglanti(p["id"], True)


@socketio.on("oyuncu:katil")
def oyuncu_katil(veri):
    with KILIT:
        try:
            o = oturum_al(veri.get("pin"))
            p = o.katil(veri.get("ad"), veri.get("token"))
        except GameError as e:
            return {"ok": False, "hata": str(e)}
        oyuncu_bagla(o, p)
        yayinla(o)
        return {"ok": True, "id": p["id"], "token": p["token"], "pin": o.pin}


@socketio.on("oyuncu:merhaba")
def oyuncu_merhaba(veri):
    with KILIT:
        try:
            o = oturum_al(veri.get("pin"))
            p = o.yeniden_baglan(veri.get("id"), veri.get("token"))
        except GameError as e:
            return {"ok": False, "hata": str(e)}
        oyuncu_bagla(o, p)
        yayinla(o)
        return {"ok": True}


def oyuncu_islem(fn):
    with KILIT:
        bag = BAGLANTILAR.get(request.sid)
        if not bag or bag[0] != "oyuncu":
            return {"ok": False, "hata": "Bağlantı doğrulanmadı, sayfayı yenile."}
        o = OTURUMLAR.get(bag[1])
        if not o:
            return {"ok": False, "hata": "Oturum sona erdi."}
        try:
            fn(o, bag[2])
        except GameError as e:
            return {"ok": False, "hata": str(e)}
        yayinla(o)
        return {"ok": True}


@socketio.on("oyuncu:cevap")
def oyuncu_cevap(veri):
    return oyuncu_islem(lambda o, pid: o.cevap(pid, veri.get("cevap")))


@socketio.on("oyuncu:takim")
def oyuncu_takim(veri):
    return oyuncu_islem(lambda o, pid: o.takim_gonder(pid, cevap=veri.get("cevap"), gerekce=veri.get("gerekce")))


@socketio.on("disconnect")
def ayrildi(*_):
    with KILIT:
        bag = BAGLANTILAR.pop(request.sid, None)
        if not bag or bag[0] != "oyuncu":
            return
        o = OTURUMLAR.get(bag[1])
        if o and OYUNCU_SID.get(o.pin, {}).get(bag[2]) == request.sid:
            OYUNCU_SID[o.pin].pop(bag[2], None)
            o.baglanti(bag[2], False)
            yayinla(o)


socketio.start_background_task(sayac_dongusu)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Yönetici ekranı:  http://localhost:{port}/yonetici\n  Telefonlar QR'daki adresten katılır ({lan_ip()}:{port}).\n")
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
