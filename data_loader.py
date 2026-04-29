import pandas as pd
import numpy as np
import streamlit as st

PORT_MAP = {
    22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS", 
    3389: "RDP", 21: "FTP", 25: "SMTP", 53: "DNS", 
    1433: "MS-SQL", 3306: "MySQL", 5060: "SIP", 
    5900: "VNC", 8080: "HTTP-Proxy"
}

@st.cache_data
def get_processed_data(file_path: str) -> pd.DataFrame:
    cols = ['datetime', 'src', 'proto', 'dpt', 'country', 'latitude', 'longitude']
    try:
        df = pd.read_csv(file_path, usecols=cols)
    except Exception as e:
        st.error(f"Błąd wczytywania: {e}")
        return pd.DataFrame()

    df['datetime'] = pd.to_datetime(df['datetime'])
    df['country'] = df['country'].fillna("Unknown").astype(str)
    df['proto'] = df['proto'].astype(str).str.upper()
    df['dpt'] = df['dpt'].fillna(0).astype(np.uint16)
    
    df['service'] = df['dpt'].map(PORT_MAP)
    df.loc[df['proto'] == 'ICMP', 'service'] = 'ICMP'
    
    mask_unknown = df['service'].isna()
    df.loc[mask_unknown, 'service'] = "Port: " + df.loc[mask_unknown, 'dpt'].astype(str)

    df['hour'] = df['datetime'].dt.hour.astype(np.uint8)
    df['day_of_week'] = df['datetime'].dt.day_name()
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=days_order, ordered=True)
    
    df['country'] = df['country'].astype('category')
    df['proto'] = df['proto'].astype('category')
    df['service'] = df['service'].astype('category')
    
    return df

def get_kpi_metrics(df: pd.DataFrame):
    if df.empty:
        return 0, 0, "N/A", "N/A"
    
    total = len(df)
    unique_ips = df['src'].nunique()
    
  
    top_p_s = df['service'].mode()
    top_p = top_p_s.iloc[0] if not top_p_s.empty else "N/A"
    
    top_pr_s = df['proto'].mode()
    top_pr = top_pr_s.iloc[0] if not top_pr_s.empty else "N/A"
    
    return total, unique_ips, top_p, top_pr