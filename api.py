"""Cardorama Forge headless simulation bridge. Experimental, not validated against live Forge."""
import os, re, secrets, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Cardorama Forge Simulation API", version="0.2.0")
FORGE = Path(os.getenv("FORGE_JAR", "/opt/forge/forge.jar"))
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = Lock()
JOBS = {}
WIN = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in\s+(\d+)\s+ms\.\s+Ai\((\d+)\)-(.+?)\s+has won!\s*$", re.M)
DRAW = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in a Draw!\s+Took\s+(\d+)\s+ms\.\s*$", re.M)

class Deck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    decklist: str = Field(min_length=1, max_length=80000)

class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: str = "commander"
    games: int = Field(default=1, ge=1, le=100)
    decks: list[Deck] = Field(min_length=2, max_length=8)

def authenticate(key):
    expected = os.getenv("CARDORAMA_API_KEY", "")
    if not expected or not key or not secrets.compare_digest(expected, key):
        raise HTTPException(401, "API key inválida")

def convert(text, title, format_name):
    if any(c in title for c in "\n\r[]="):
        raise ValueError("Nome de deck inválido")
    commander, main = [], []
    area = "main"
    ignore = {"sideboard","maybeboard","considering","tokens","token"}
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        heading = s.strip("[]").strip().lower().rstrip(":")
        if heading in {"commander","commanders","main","deck","creatures","lands","artifacts","instants","sorceries","enchantments","planeswalkers"} | ignore and not re.match(r"^\d+\s", s):
            area = "commander" if heading in ("commander", "commanders") else "skip" if heading in ignore else "main"
            continue
        if area == "skip":
            continue
        m = re.fullmatch(r"\s*(\d{1,3})\s+(.+?)\s*", s)
        if not m:
            raise ValueError(f"Linha {i}: formato inválido")
        qty, card = int(m.group(1)), m.group(2)
        card = re.sub(r"\s+\([A-Za-z0-9]{2,8}\)\s+\d+[a-z]?\s*(?:\*F\*)?$","", card)
        if not 1 <= qty <= 99 or len(card)>180 or any(ord(c)<32 for c in card):
            raise ValueError(f"Linha {i}: carta ou quantidade inválida")
        (commander if area == "commander" else main).append((qty,card))
    count = sum(q for q,_ in main+commander)
    if format_name == "commander" and (count != 100 or sum(q for q,_ in commander) not in (1,2)):
        raise ValueError("Commander requer 100 cartas e um ou dois comandantes")
    if not 2 <= count <= 500:
        raise ValueError("Quantidade total inválida")
    rows = ["[metadata]",f"Name={title}","[Main]"]
    rows += [f"{q} {n}" for q,n in main]
    if commander:
        rows += ["[Commander]"]+[f"{q} {n}" for q,n in commander]
    return "\n".join(rows)+"\n"

@app.get("/healthz")
def health():
    return {"status":"ok","engine_present":FORGE.is_file(),"version":"not-verified"}

@app.get("/readyz")
def ready():
    if not FORGE.is_file():
        raise HTTPException(503, "Forge jar ausente")
    return {"ready":True,"caution":"Jar presente; funcionalidade exige teste real"}

def run_job(id, body):
    with LOCK:
        JOBS[id]["status"] = "running"
    try:
        with tempfile.TemporaryDirectory(prefix="cardorama-") as directory:
            filenames = []
            for i,d in enumerate(body.decks,1):
                filename = f"player_{i}.dck"
                Path(directory,filename).write_text(convert(d.decklist,d.name,body.format),encoding="utf-8")
                filenames.append(filename)
            heap = max(256,min(8192,int(os.getenv("FORGE_HEAP_MB","512"))))
            cmd = ["java",f"-Xmx{heap}m","-Djava.awt.headless=true","-jar",str(FORGE),"sim","-d",*filenames,"-D",directory,"-n",str(body.games),"-f",body.format,"-q","-c",str(int(os.getenv("FORGE_GAME_CLOCK","90")))]
            timeout = max(30,min(7200,int(os.getenv("FORGE_TIMEOUT","600"))))
            completed = subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",timeout=timeout,cwd=str(FORGE.parent),env={k:v for k,v in os.environ.items() if k in ("PATH","HOME","LANG","JAVA_HOME","TMPDIR")},check=False)
            output = completed.stdout[-80000:]
        winners = {}
        for match in WIN.finditer(output):
            n, ms, player, reported = match.groups()
            player = int(player)
            if player < 1 or player > len(body.decks) or reported != body.decks[player-1].name or int(n) in winners: continue
            winners[int(n)] = {"winner":player,"duration_ms":int(ms)}
        for match in DRAW.finditer(output):
            n,ms = map(int,match.groups())
            if n not in winners: winners[n] = {"winner":None,"duration_ms":ms}
        valid = sorted(winners) == list(range(1,body.games+1)) and output.count("Game Result:")==body.games and not re.search(r"Could not load deck|No deck found|Exception in thread|Game threw exception",output,re.I)
        result = {"status":"completed" if completed.returncode == 0 and valid else "failed","exit_code":completed.returncode,"games_completed":len(winners),"results":[{"game":n,**winners[n]} for n in sorted(winners)],"raw_output":output,"warning":"Simulações IA contra IA, não probabilidades de vitória contra humanos"}
    except Exception as exc:
        result = {"status":"failed","error":str(exc)}
    with LOCK:
        JOBS[id].update(result)
        JOBS[id]["finished_at"] = datetime.now(timezone.utc).isoformat()

@app.post("/v1/simulations", status_code=202)
def submit(body:Request,x_api_key:str|None=Header(default=None)):
    authenticate(x_api_key)
    if not FORGE.is_file():
        raise HTTPException(503,"Forge indisponível")
    if body.format.lower() not in ("commander","constructed","oathbreaker","tinyleaders","brawl"):
        raise HTTPException(422,"Formato inválido")
    try:
        for d in body.decks: convert(d.decklist,d.name,body.format.lower())
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    with LOCK:
        if sum(j["status"] in ("queued","running") for j in JOBS.values()) >= 3:
            raise HTTPException(429,"Fila cheia")
        if len(JOBS)>500:
            for key in list(JOBS):
                if JOBS[key]["status"] not in ("queued","running"): del JOBS[key]
                if len(JOBS)<=450: break
        jobid = str(uuid4())
        JOBS[jobid] = {"id":jobid,"status":"queued","games_requested":body.games,"submitted_at":datetime.now(timezone.utc).isoformat()}
    POOL.submit(run_job,jobid,body)
    return {"id":jobid,"poll":f"/v1/simulations/{jobid}","status":"queued"}

@app.get("/v1/simulations/{jobid}")
def get_job(jobid:str,x_api_key:str|None=Header(default=None)):
    authenticate(x_api_key)
    with LOCK:
        if jobid not in JOBS: raise HTTPException(404,"Job não encontrado")
        return dict(JOBS[jobid])

# A one-shot staging smoke test: execution occurs on Railway, never on a mock engine.
# Disable CARDORAMA_SELFTEST_GAMES after testing. The service can remain private.
import json as _json
from threading import Thread as _Thread

@app.on_event("startup")
def _start_smoke_test():
    count_raw = os.getenv("CARDORAMA_SELFTEST_GAMES")
    if not count_raw:
        return
    try:
        count = int(count_raw)
        if count < 1 or count > 10:
            raise ValueError("selftest supports 1 through 10 games")
        deck = Path(__file__).with_name("examples").joinpath("sliver_demonstration.txt").read_text(encoding="utf-8")
        entry = Deck(name="Sliver Demonstration", decklist=deck)
        payload = Request(format="commander", games=count, decks=[entry, entry])
        for d in payload.decks:
            convert(d.decklist,d.name,payload.format)
    except Exception as exc:
        print("CARDORAMA_SELFTEST_ERROR="+str(exc), flush=True)
        return
    jid = "staging-"+str(uuid4())
    with LOCK:
        JOBS[jid] = {"id":jid,"status":"queued","games_requested":count}
    def run():
        print("CARDORAMA_SELFTEST_START="+_json.dumps({"job":jid,"games":count,"deck":"Sliver Demonstration vs itself","forge_jar":str(FORGE)}),flush=True)
        run_job(jid,payload)
        record = dict(JOBS[jid])
        if "raw_output" in record:
            output = record.pop("raw_output")
            record["engine_output_tail"] = output[-12000:]
        print("CARDORAMA_SELFTEST_RESULT="+_json.dumps(record,ensure_ascii=False),flush=True)
    _Thread(target=run,daemon=True,name="cardorama-staging-selftest").start()
