import urllib.request
import json
import sys

VALVE_URL = "https://www.dota2.com/webapi/ILeaderboard/GetDivisionLeaderboard/v0001?division=europe&leaderboard=0"

def run_agent():
    print("Rozpoczynam pobieranie danych od Valve...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    req = urllib.request.Request(VALVE_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            raw_response = response.read().decode()
            print(f"Odpowiedź pobrana pomyślnie. Długość: {len(raw_response)} znaków.")
            data = json.loads(raw_response)
    except Exception as e:
        print(f"Błąd krytyczny podczas pobierania danych: {e}")
        sys.exit(1) 

    # 1. Sprawdzamy klucze w głównym JSONie
    print("Klucze od Valve:", list(data.keys()))
    
    # 2. Pobieramy tablicę graczy
    leaderboard = data.get("leaderboard", [])
    print(f"Znalazłem {len(leaderboard)} graczy w głównej tabeli.")
    
    # 3. Sprawdzamy, jak wygląda pierwszy gracz na liście
    if len(leaderboard) > 0:
        print("Struktura przykładowego gracza:", json.dumps(leaderboard[0], indent=2))
    else:
        print("UWAGA: Valve nie zwróciło żadnych graczy! Pełna odpowiedź to:")
        print(json.dumps(data, indent=2))

   # 4. Bezpieczne filtrowanie Polaków + Biała/Czarna Lista
    WHITELIST = ["Jacob^", "Ekki", "Kubanos", "Miyagi", "OnlyMatt", "RaizQT", "Ged", "eejit", "L1Z4RD"] 
    BLACKLIST = ["Oszust1", "FakePolak", "1αmW7ll", "bloodr4yne", "L1Z4RD" , "Krinzhik", "jerk god", "slime pidor"] # <-- Tutaj wpisujesz trolli
    
    polish_players = []
    for p in leaderboard:
        country = p.get("country")
        name = p.get("name")
        
        # 1. CZARNA LISTA: Sprawdzamy, czy gracz jest zablokowany
        is_blacklisted = name and name.lower() in [b.lower() for b in BLACKLIST]
        if is_blacklisted:
            continue # Jeśli jest na czarnej liście, całkowicie go ignorujemy i idziemy dalej
            
        # 2. STANDARDOWE SPRAWDZENIE: Czy gracz ma kraj PL?
        is_polish_by_country = country and isinstance(country, str) and country.lower() == "pl"
        
        # 3. BIAŁA LISTA: Czy gracz jest na liście wyjątków?
        is_on_whitelist = name and name.lower() in [w.lower() for w in WHITELIST]
        
        # 4. WYNIK: Jeśli ma PL lub jest na białej liście (a nie odrzuciła go czarna lista) -> dodajemy
        if is_polish_by_country or is_on_whitelist:
            polish_players.append(p)
    
    print(f"Wyfiltrowano {len(polish_players)} graczy z Polski w Top 5000.")

    # 5. Zapis
    output_filename = "polish_top.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(polish_players, f, indent=2)

if __name__ == "__main__":
    run_agent()
