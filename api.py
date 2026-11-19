"""Cardorama Forge headless simulation bridge. Experimental, not validated against live Forge."""
import os, re, secrets, subprocess, tempfile
from parsing import parse_results
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from details import extract_details
from fastapi import Query

app = FastAPI(title="Cardorama Forge Simulation API", version="0.4.0")
FORGE = Path(os.getenv("FORGE_JAR", "/opt/forge/forge.jar"))
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = Lock()
JOBS = {}
DETAILS = {}
WIN = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in\s+(\d+)\s+ms\.\s+Ai\((\d+)\)-(.+?)\s+has won!\s*$", re.M)
DRAW = re.compile(r"^\s*Game Result:\s*Game\s+(\d+)\s+ended in a Draw!\s+Took\s+(\d+)\s+ms\.\s*$", re.M)

class Deck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    decklist: str = Field(min_length=1, max_length=80000)

class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: str = "commander"
    mode: str = "summary"  # summary | detailed
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
            detailed = body.mode == "detailed"
            cmd = ["java",f"-Xmx{heap}m","-Djava.awt.headless=true","-jar",str(FORGE),"sim","-d",*filenames,"-D",directory,"-n",str(body.games),"-f",body.format]
            if not detailed:
                cmd.append("-q")
            cmd += ["-c",str(int(os.getenv("FORGE_GAME_CLOCK","300")))]
            timeout = max(30,min(7200,int(os.getenv("FORGE_TIMEOUT","3600"))))
            # Disk-backed log avoids subprocess.PIPE retaining unbounded verbose game logs.
            with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
                completed = subprocess.run(cmd,stdout=stdout_file,stderr=stderr_file,timeout=timeout,cwd=str(FORGE.parent),env={k:v for k,v in os.environ.items() if k in ("PATH","HOME","LANG","JAVA_HOME","TMPDIR")},check=False)
                byte_limit = 16_000_000 if detailed else 160_000
                stdout_file.seek(0,2)
                output_bytes = stdout_file.tell()
                truncated = output_bytes > byte_limit
                stdout_file.seek(0)
                output = stdout_file.read(byte_limit).decode("utf-8",errors="replace")
                stderr_file.seek(0,2)
                error_bytes = stderr_file.tell()
                stderr_file.seek(max(0,error_bytes-12_000))
                error_output = stderr_file.read().decode("utf-8",errors="replace")
        parsed = parse_results(output, body.games, [d.name for d in body.decks], int(os.getenv("FORGE_GAME_CLOCK","300")))
        fatal = bool(re.search(r"Could not load deck|No deck found|Exception in thread|Game threw exception", output + error_output, re.I))
        ok = completed.returncode == 0 and parsed["valid"] and not fatal and not truncated
        status = "completed" if ok and parsed["timeouts"] == 0 else "partial" if ok else "failed"
        result = {"status":status,"exit_code":completed.returncode,**parsed,"log_truncated":truncated,"log_bytes":output_bytes,"stderr_tail":error_output[-2000:],"warning":"IA contra IA; interrupções por tempo não são vitórias, mesmo que o Forge exiba vencedor"}
        if detailed:
            details = extract_details(output, [d.decklist for d in body.decks],body.games)
            if details["events_exceeded"]:
                result["status"]="partial"
            with LOCK:
                DETAILS[id]=details["games"]
            result["detail"]={"events_captured":details["events_captured"],"games_with_logs":details["games_with_logs"],"events_exceeded":details["events_exceeded"],"limitations":details["limitations"]}
            result["card_analysis"]=details["card_analysis"]
            result["logs_available_via"]=f"/v1/simulations/{id}/games/{{game_number}}"
        else:
            result["raw_output"]=output[-16000:]
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
    if body.mode not in ("summary","detailed"):
        raise HTTPException(422,"Modo inválido")
    if body.mode == "detailed" and body.games > 10:
        raise HTTPException(422,"Limite de 10 partidas no modo detalhado, durante homologação")
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

@app.get("/v1/simulations/{jobid}/games/{game_number}")
def get_game_events(jobid: str,game_number:int, x_api_key:str|None=Header(default=None),turn:int|None=Query(default=None,ge=1),offset:int=Query(default=0,ge=0),limit:int=Query(default=200,ge=1,le=1000)):
    authenticate(x_api_key)
    with LOCK:
        if jobid not in JOBS:
            raise HTTPException(404,"Job não encontrado")
        if jobid not in DETAILS or game_number not in DETAILS[jobid]:
            raise HTTPException(404,"Histórico detalhado indisponível para esta partida")
        events=DETAILS[jobid][game_number]
        selected=[e for e in events if turn is None or e["turn"]==turn]
        return {"job":jobid,"game":game_number,"turn":turn,"total":len(selected),"offset":offset,"limit":limit,"events":selected[offset:offset+limit],"volatile":True}

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
        payload = Request(format="commander", mode=os.getenv("CARDORAMA_SELFTEST_MODE","summary"), games=count, decks=[entry, entry])
        for d in payload.decks:
            convert(d.decklist,d.name,payload.format)
    except Exception as exc:
        print("CARDORAMA_SELFTEST_ERROR="+str(exc), flush=True)
        return
    jid = "staging-"+str(uuid4())
    with LOCK:
        JOBS[jid] = {"id":jid,"status":"queued","games_requested":count}
    def run():
        print("CARDORAMA_SELFTEST_START="+_json.dumps({"job":jid,"games":count,"mode":payload.mode,"deck":"Sliver Demonstration vs itself","forge_jar":str(FORGE)}),flush=True)
        run_job(jid,payload)
        record = dict(JOBS[jid])
        if "raw_output" in record:
            output = record.pop("raw_output")
            record["engine_output_tail"] = output[-1600:]
        if "card_analysis" in record:
            record["card_analysis"]={n:a for n,a in record["card_analysis"].items() if a["signal"]!="not_observed"}
        record.pop("stderr_tail",None)
        print("CARDORAMA_SELFTEST_RESULT="+_json.dumps(record,ensure_ascii=False),flush=True)
    _Thread(target=run,daemon=True,name="cardorama-staging-selftest").start()
