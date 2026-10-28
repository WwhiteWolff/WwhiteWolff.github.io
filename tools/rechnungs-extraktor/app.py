from flask import Flask, Response, jsonify, render_template_string, request

import extractor

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
ALLOWED = {"application/pdf", "image/png", "image/jpeg", "image/webp"}

PAGE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rechnungs-Extraktor</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>body{font-family:'Inter',sans-serif;background:#fbfbfd}</style></head>
<body class="text-gray-900"><main class="max-w-4xl mx-auto px-6 py-14">
<h1 class="text-4xl font-bold tracking-tight mb-2">Rechnungs-Extraktor</h1>
<p class="text-gray-500 mb-8">Rechnungen hochladen, Daten automatisch auslesen, als Excel-CSV für den Steuerberater exportieren.</p>
<details id="settings" class="mb-6 bg-white border border-gray-200 rounded-2xl px-5 py-4" {% if demo %}open{% endif %}>
  <summary class="cursor-pointer text-sm font-medium">Einstellungen: OpenAI-Key <span id="keystate" class="text-gray-400"></span></summary>
  <p class="text-sm text-gray-500 mt-3">Ohne Key läuft der Demo-Modus mit Beispieldaten. Der Key wird im Schlüsselbund deines Systems gespeichert, nicht in einer Datei.</p>
  <div class="flex gap-2 mt-3"><input id="key" type="password" placeholder="sk-..." class="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-black">
  <button id="savekey" class="bg-black text-white px-5 py-2 rounded-full text-sm">Speichern</button>
  <button id="delkey" class="border border-gray-300 px-5 py-2 rounded-full text-sm">Entfernen</button></div>
</details>
<label id="drop" class="block border-2 border-dashed border-gray-300 rounded-3xl bg-white p-12 text-center cursor-pointer hover:border-black transition-colors">
  <span class="text-lg font-semibold">PDFs oder Fotos hierher ziehen</span><br><span class="text-sm text-gray-500">oder klicken zum Auswählen</span>
  <input id="files" type="file" multiple accept=".pdf,image/png,image/jpeg,image/webp" class="hidden">
</label>
<p id="status" class="text-sm text-gray-500 mt-4 h-5"></p>
<div id="result" class="hidden mt-6">
  <div class="overflow-x-auto bg-white rounded-3xl border border-gray-200"><table class="w-full text-sm">
    <thead class="text-left text-gray-500"><tr id="head"></tr></thead><tbody id="body"></tbody></table></div>
  <button id="export" class="mt-6 bg-black text-white px-8 py-3 rounded-full font-medium hover:bg-gray-800 transition-all">Als CSV exportieren</button>
</div></main>
<script>
const COLS=[["datum","Datum"],["rechnungsnummer","Rechnungsnr."],["lieferant","Lieferant"],["netto","Netto"],["mwst_satz","MwSt %"],["brutto","Brutto"]];
const rows=[], $=id=>document.getElementById(id);
$("head").innerHTML=COLS.map(c=>`<th class="px-4 py-3 font-medium">${c[1]}</th>`).join("");
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render(){
  $("result").classList.toggle("hidden",!rows.length);
  $("body").innerHTML=rows.map((r,i)=>"<tr class='border-t border-gray-100'>"+COLS.map(c=>
    `<td class="px-4 py-2 ${c[0]==="lieferant"?"min-w-[15rem]":""}"><input data-i="${i}" data-k="${c[0]}" value="${esc(r[c[0]])}" class="w-full bg-transparent rounded px-1 py-1 focus:bg-gray-100 outline-none"></td>`).join("")+"</tr>").join("");
}
$("body").addEventListener("input",e=>{const t=e.target;rows[t.dataset.i][t.dataset.k]=t.value;});
async function upload(list){
  for(const [n,f] of [...list].entries()){
    $("status").textContent=`Lese ${f.name} (${n+1}/${list.length}) …`;
    const fd=new FormData();fd.append("file",f);fd.append("index",rows.length);
    const res=await fetch("/extract",{method:"POST",body:fd});
    const j=await res.json();
    if(!res.ok){$("status").textContent=`Fehler bei ${f.name}: ${j.error}`;return;}
    rows.push(j);render();
  }
  $("status").textContent=`${rows.length} Rechnung(en) ausgelesen. Werte lassen sich direkt in der Tabelle korrigieren.`;
}
async function keyState(){const j=await (await fetch("/api/key")).json();$("keystate").textContent=j.demo?"· Demo-Modus":"· gespeichert";}
async function keyCall(method,body){const r=await fetch("/api/key",{method,headers:{"Content-Type":"application/json"},body});if(!r.ok)alert((await r.json()).error);$("key").value="";keyState();}
$("savekey").addEventListener("click",()=>keyCall("POST",JSON.stringify({key:$("key").value})));
$("delkey").addEventListener("click",()=>keyCall("DELETE"));
keyState();
$("files").addEventListener("change",e=>upload(e.target.files));
$("drop").addEventListener("dragover",e=>e.preventDefault());
$("drop").addEventListener("drop",e=>{e.preventDefault();upload(e.dataTransfer.files);});
$("export").addEventListener("click",async()=>{
  const res=await fetch("/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(rows)});
  const a=document.createElement("a");a.href=URL.createObjectURL(await res.blob());a.download="rechnungen.csv";a.click();
});
</script></body></html>"""


@app.get("/")
def index():
    return render_template_string(PAGE, demo=extractor.demo_mode())


@app.route("/api/key", methods=["GET", "POST", "DELETE"])
def api_key():
    try:
        if request.method == "POST":
            key = ((request.get_json(silent=True) or {}).get("key") or "").strip()
            if not key.startswith("sk-"):
                return jsonify(error="Ungültiger Key. Er beginnt mit sk-."), 400
            extractor.save_key(key)
        elif request.method == "DELETE":
            extractor.delete_key()
    except Exception as e:
        return jsonify(error=f"Schlüsselbund-Fehler: {e}"), 500
    return jsonify(demo=extractor.demo_mode())


@app.post("/extract")
def extract():
    f = request.files.get("file")
    if not f or f.mimetype not in ALLOWED:
        return jsonify(error="Nur PDF, PNG, JPG oder WebP erlaubt."), 400
    try:
        row = extractor.extract(f.filename, f.read(), f.mimetype, int(request.form.get("index", 0)))
    except Exception as e:  # API-Fehler an die UI durchreichen
        return jsonify(error=str(e)), 502
    return jsonify(row)


@app.post("/export")
def export():
    rows = request.get_json(silent=True)
    if not isinstance(rows, list):
        return jsonify(error="Ungültige Daten."), 400
    return Response(extractor.to_csv(rows), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rechnungen.csv"})


if __name__ == "__main__":
    app.run(port=5050, debug=True)
