import urllib.request
import json

# Oficjalny endpoint Valve dla Europy
VALVE_URL = "https://www.dota2.com/webapi/ILeaderboard/GetDivisionLeaderboard/v0001?division=europe"

def run_agent():
    print("Rozpoczynam pobieranie danych od Valve...")
    
    # Dodajemy nagłówek User-Agent, żeby Valve nie zablokowało zapytania jako bota
    req = urllib.request.Request(VALVE_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Błąd podczas pobierania danych: {e}")
        return

    # Filtrujemy tylko graczy, którzy mają ustawiony kraj na Polskę ("pl")
    polish_players = [
        player for player in data.get("leaderboard", [])
        if player.get("country", "").lower() == "pl"
    ]
    
    print(f"Znaleziono {len(polish_players)} graczy z Polski w Top 5000.")

    # Zapisujemy wynik do pliku
    output_filename = "polish_top.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(polish_players, f, indent=2)
        
    print(f"Zapisano dane do {output_filename}")

if __name__ == "__main__":
    run_agent()
