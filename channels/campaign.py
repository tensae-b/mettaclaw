
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT_DIR / "memory"
CLIENT_DB_PATH = MEMORY_DIR / "clients.json"
CHANNELS_DIR = ROOT_DIR / "channels"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _slug(value):
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip()).strip("_")
    return slug or "client"


def _metta_string(value):
    text = str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _load_db():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not CLIENT_DB_PATH.exists():
        return {"clients": {}}
    with CLIENT_DB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("clients", {})
    return data


def _save_db(data):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CLIENT_DB_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(CLIENT_DB_PATH)


def _client_key(data, brand):
    requested = str(brand).strip()
    for key in data["clients"]:
        if key.casefold() == requested.casefold():
            return key
    return requested


def _ensure_client(data, brand):
    key = _client_key(data, brand)
    if key not in data["clients"]:
        data["clients"][key] = {
            "name": key,
            "profile": "",
            "campaigns": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
    return key, data["clients"][key]


def _campaign_output_path(brand):
    return CHANNELS_DIR / f"campaign-{_slug(brand)}.txt"


def _append_campaign_file(brand, concept, result):
    output_path = _campaign_output_path(brand)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== Campaign Ideas for: {brand} ===\n")
        f.write(f"Concept: {concept}\n")
        f.write(result)
        f.write("\n")


def _append_error_file(brand, error):
    output_path = _campaign_output_path(brand)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== ERROR for: {brand} ===\n{error}\n")


def _format_previous_campaigns(client, limit=5):
    campaigns = client.get("campaigns", [])[-limit:]
    if not campaigns:
        return "No saved previous campaigns for this client."
    chunks = []
    for campaign in campaigns:
        chunks.append(
            "Created: {created_at}\nConcept: {concept}\nIdeas:\n{ideas}".format(
                created_at=campaign.get("created_at", "unknown"),
                concept=campaign.get("concept", ""),
                ideas=campaign.get("ideas", ""),
            )
        )
    return "\n\n---\n\n".join(chunks)


def _build_prompt(brand, concept, profile, previous_campaigns, max_ideas):
    profile_text = profile.strip() or "No saved client profile or brand guidelines yet."
    return (
        "You are a senior marketing strategist generating campaign ideas for a client.\n\n"
        f"Client: {brand}\n\n"
        "Saved client profile, branding, and constraints:\n"
        f"{profile_text}\n\n"
        "New campaign concept note:\n"
        f"{concept}\n\n"
        "Previous campaign ideas for this client:\n"
        f"{previous_campaigns}\n\n"
        f"Generate exactly {max_ideas} new campaign ideas.\n"
        "Requirements:\n"
        "- Fit the saved client profile and brand voice.\n"
        "- Use the previous campaign history as context, but avoid repeating old titles or core ideas.\n"
        "- Make each idea specific enough that a creative team could start from it.\n\n"
        "Format your response as:\n"
        "1. [Title]: [Description]\n"
        "2. [Title]: [Description]\n"
        "3. [Title]: [Description]"
    )


def _latest_campaign_ideas(client, concept):
    wanted = str(concept).strip()
    for campaign in reversed(client.get("campaigns", [])):
        if campaign.get("source") == "generated" and campaign.get("concept") == wanted:
            return campaign.get("ideas", "")
    campaigns = client.get("campaigns", [])
    if campaigns:
        return campaigns[-1].get("ideas", "")
    return ""


def _compact_message(text, max_chars=1200):
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    compact = "\n".join(lines[:6])
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rstrip() + "..."
    return compact


def campaign_start_message(brand, concept):
    return (
        f"Generating 3 campaign ideas for {brand} using saved client profile "
        f"and previous campaign memory. Concept: {concept}"
    )


def campaign_done_message(brand, concept, command_result=""):
    if str(command_result).startswith("(ERROR"):
        return f"Campaign generation failed for {brand}. Check the local campaign error file for details."

    data = _load_db()
    key = _client_key(data, brand)
    client = data["clients"].get(key)
    ideas = _latest_campaign_ideas(client, concept) if client else ""
    if not ideas:
        return f"Done generating campaign ideas for {brand}, but I could not find a saved result."

    return f"Done. Saved campaign ideas for {key}.\n{_compact_message(ideas)}"


def save_client_profile(brand, profile):
    data = _load_db()
    key, client = _ensure_client(data, brand)
    client["profile"] = str(profile).strip()
    client["updated_at"] = _now()
    _save_db(data)
    return f"(CLIENT_PROFILE_SAVED {_metta_string(key)})"


def get_client_profile(brand):
    data = _load_db()
    key = _client_key(data, brand)
    client = data["clients"].get(key)
    if not client:
        return f"(CLIENT_PROFILE_MISSING {_metta_string(brand)})"
    return f"(CLIENT_PROFILE {_metta_string(key)} {_metta_string(client.get('profile', ''))})"


def list_clients():
    data = _load_db()
    clients = " ".join(_metta_string(key) for key in sorted(data["clients"]))
    return f"(CLIENTS ({clients}))"


def add_client_campaign(brand, concept, ideas):
    data = _load_db()
    key, client = _ensure_client(data, brand)
    client.setdefault("campaigns", []).append(
        {
            "created_at": _now(),
            "concept": str(concept).strip(),
            "ideas": str(ideas).strip(),
            "source": "manual",
        }
    )
    client["updated_at"] = _now()
    _save_db(data)
    return f"(CLIENT_CAMPAIGN_SAVED {_metta_string(key)})"


def client_campaign_history(brand, limit=5):
    data = _load_db()
    key = _client_key(data, brand)
    client = data["clients"].get(key)
    if not client:
        return f"(CLIENT_CAMPAIGN_HISTORY_MISSING {_metta_string(brand)})"
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
    history = _format_previous_campaigns(client, limit=limit)
    return f"(CLIENT_CAMPAIGN_HISTORY {_metta_string(key)} {_metta_string(history)})"

def campaign_ideas(brand, concept, max_ideas=3):
    try:
        data = _load_db()
        key, client = _ensure_client(data, brand)
        previous_campaigns = _format_previous_campaigns(client)
        prompt = _build_prompt(
            key,
            concept,
            client.get("profile", ""),
            previous_campaigns,
            max_ideas,
        )

        payload = json.dumps({
            "model": "qwen2.5:14b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            OLLAMA_CHAT_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))

        result = body["message"]["content"]

        client.setdefault("campaigns", []).append(
            {
                "created_at": _now(),
                "concept": str(concept).strip(),
                "ideas": result,
                "source": "generated",
            }
        )
        client["updated_at"] = _now()
        _save_db(data)
        _append_campaign_file(key, concept, result)

        ret = "("
        for line in result.strip().split("\n"):
            if line.strip():
                ret += "(IDEA: " + line.strip() + ") "
        ret += ")"
        return ret

    except Exception as e:
        _append_error_file(brand, str(e))
        return f"(ERROR {_metta_string(str(e))})"
