import redis
import time
import random

print("Uruchamianie generatora logów na żywo dla chmury (Producent)...")

try:
    # Wklej tu DOKŁADNIE swoje dane z Upstash
    r = redis.Redis(
        host='https://literate-collie-68924.upstash.io',
        port=6379,
        password='gQAAAAAAAQ08AAIgcDE0MWE5NGMzYjU1OTY0ZjRkOTk0MmZiMWY2NjE3Njk1ZA',
        ssl=True,
        db=0,
        decode_responses=True
    )
    r.ping()
    print("Połączono z chmurą Upstash pomyślnie!")
except Exception as e:
    print(f"BŁĄD: Nie można połączyć z Redisem w chmurze. {e}")
    exit()

kraje = ["RU", "CN", "BR", "US", "IR", "KP", "VN"]
porty = [22, 3389, 80, 443, 21, 53, 445]

while True:
    ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    log_entry = f"[ALERT NA ŻYWO] Haker z {random.choice(kraje)} (IP: {ip}) uderzył w port {random.choice(porty)}"
    
    # Wrzucamy do kolejki
    r.lpush("live_soc_buffer", log_entry)
    # Trzymamy tylko 100 ostatnich, żeby nie zapchać RAMu
    r.ltrim("live_soc_buffer", 0, 99)
    
    print(f"Wysłano do bufora: {log_entry}")
    time.sleep(2)