"""Assemble la page : données + repères, chiffrés avec le mot de passe.
Usage : python3 build.py data.json "<mot de passe>" > index.html
"""
import sys, json, os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

HERE = os.path.dirname(os.path.abspath(__file__))
ITER = 250_000

REPERES = {
    "source": "Repères : équipe fourrage CA43 (repris du fichier de synthèse).",
    "herbe": [
        {"seuil": 200, "label": "200°", "court": "Démarrage de la végétation",
         "texte": "Démarrage de la végétation des graminées des prairies précoces (en altitude)."},
        {"seuil": 250, "label": "250°", "court": "Mise à l'herbe des laitières",
         "texte": "Lâcher les vaches laitières."},
        {"seuil": 300, "label": "300°", "court": "Mise à l'herbe jour et nuit",
         "texte": "Troupeaux qui ne rentrent pas pour la nuit."},
        {"seuil": 500, "label": "500°", "court": "Fin du déprimage",
         "texte": "Arrêter le déprimage."},
        {"seuil": 750, "label": "750°", "court": "Début épiaison des précoces",
         "texte": "Début épiaison des espèces précoces : ray-grass anglais, flouve, vulpin."},
        {"seuil": 850, "label": "850–1000°", "court": "Pleine épiaison des précoces",
         "texte": "Pleine épiaison des espèces précoces."},
        {"seuil": 900, "label": "900°", "court": "Début épiaison des tardives",
         "texte": "Début épiaison des espèces plus tardives : dactyle, fétuque, fléole."},
        {"seuil": 1200, "label": "1200–1400°", "court": "Pleine épiaison des tardives",
         "texte": "Pleine épiaison des espèces tardives."},
        {"seuil": None, "label": "Foin", "court": "",
         "texte": "Pour les prairies plus tardives conduites en foin, le démarrage est plus lent."},
    ],
    "autres": [
        {"label": "200°", "texte": "Céréales d'automne : la végétation démarre vers 200° base 0 depuis le 1er janvier. Prévoir les apports d'azote un peu avant."},
        {"label": "80–120°", "base6": True, "texte": "Levée de l'herbe : 80 à 120° base 6 selon la longueur du jour."},
        {"label": "44°", "base6": True, "texte": "Formation d'une feuille : 44° base 6."},
    ],
}


PWA_HEAD = """<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<style>
header.top, #detail header { padding-top: calc(10px + env(safe-area-inset-top)); }
#lock { padding-top: calc(24px + env(safe-area-inset-top)); }
main, header.top, footer.src { padding-left: max(16px, env(safe-area-inset-left)); padding-right: max(16px, env(safe-area-inset-right)); }
</style>"""
PWA_BODY = """<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => { navigator.serviceWorker.register("sw.js").catch(() => {}); });
}
</script>"""


def encrypt(obj, password):
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(password.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), None)
    e = lambda b: base64.b64encode(b).decode()
    return {"salt": e(salt), "iv": e(iv), "iter": ITER, "ct": e(ct)}


def main(data_path, password):
    data = json.load(open(data_path))
    payload = encrypt({"data": data, "reperes": REPERES}, password)
    html = open(os.path.join(HERE, "template.html")).read()
    calc = open(os.path.join(HERE, "calc.js")).read()
    html = html.replace("__CALC__", calc).replace("__PAYLOAD__", json.dumps(payload))
    if os.environ.get("PV43_PWA") == "1":
        html = html.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
                            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
        html = html.replace("<!--PWA_HEAD-->", PWA_HEAD).replace("<!--PWA_BODY-->", PWA_BODY)
    sys.stdout.write(html)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
