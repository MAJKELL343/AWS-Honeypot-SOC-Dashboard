import pandas as pd

# Wczytaj swój pełny plik
df = pd.read_csv("AWS_Honeypot_marx-geo.csv")

# Zapisz go jako skompresowany plik .gz
# To zajmie znacznie mniej miejsca i GitHub to przyjmie
df.to_csv("AWS_Honeypot_marx-geo.csv.gz", index=False, compression="gzip")

print("Gotowe! Masz teraz plik AWS_Honeypot_marx-geo.csv.gz")