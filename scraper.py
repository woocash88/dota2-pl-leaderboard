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

   # 4. Bezpieczne filtrowanie Polaków + Biała Lista (Override)
    # Wpisz tutaj dokładne nicki graczy, których chcesz dodać
    WHITELIST = ["Gracz1", "Gracz2", "Gracz3"] 
    
    polish_players = []
    for p in leaderboard:
        country = p.get("country")
        name = p.get("name")
        
        # Sprawdzamy, czy gracz ma kraj PL
        is_polish_by_country = country and isinstance(country, str) and country.lower() == "pl"
        
        # Sprawdzamy, czy gracz jest na naszej liście wyjątków
        # Zamieniamy wszystkie nicki na małe litery przed porównaniem
        is_on_whitelist = name and name.lower() in [w.lower() for w in WHITELIST]
        
        if is_polish_by_country or is_on_whitelist:
            polish_players.append(p)
    
    print(f"Wyfiltrowano {len(polish_players)} graczy z Polski w Top 5000.")

    # 5. Zapis
    output_filename = "polish_top.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(polish_players, f, indent=2)

if __name__ == "__main__":
    run_agent()
