"""Cada mañana: previsión de 7 días para Madrid (Open-Meteo, gratis y sin clave) → tiempo.json.
La app la usa para proponer planes de interior si llueve o hace frío, y terrazas si hace bueno."""
import json, sys, datetime, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = ('https://api.open-meteo.com/v1/forecast?latitude=40.4168&longitude=-3.7038&timezone=Europe%2FMadrid&forecast_days=7'
       '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max')
DESC = {0: 'Despejado', 1: 'Casi despejado', 2: 'Algunas nubes', 3: 'Nublado', 45: 'Niebla', 48: 'Niebla', 51: 'Llovizna', 53: 'Llovizna', 55: 'Llovizna',
        61: 'Lluvia débil', 63: 'Lluvia', 65: 'Lluvia fuerte', 71: 'Nieve', 73: 'Nieve', 75: 'Nieve fuerte', 80: 'Chubascos', 81: 'Chubascos', 82: 'Chubascos fuertes',
        95: 'Tormenta', 96: 'Tormenta', 99: 'Tormenta'}
ICON = lambda c: '☀️' if c <= 1 else '⛅' if c == 2 else '☁️' if c == 3 else '🌫️' if c in (45, 48) else '🌨️' if 71 <= c <= 77 else '⛈️' if c >= 95 else '🌧️'

def main():
    raw = open(sys.argv[1], encoding='utf-8').read() if len(sys.argv) > 1 else \
        urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'RENTA/1.0'}), timeout=30).read().decode()
    d = json.loads(raw)['daily']
    dias = []
    for k, fecha in enumerate(d['time']):
        c = int(d['weather_code'][k] or 0); pr = d['precipitation_probability_max'][k] or 0; tmax = d['temperature_2m_max'][k]; tmin = d['temperature_2m_min'][k]
        viento = d['wind_speed_10m_max'][k] or 0
        if pr >= 50 or c >= 51 or tmax < 10: plan = 'interior'
        elif tmax >= 17 and pr < 25 and c <= 2 and viento < 35: plan = 'exterior'
        else: plan = 'mixto'
        dias.append({'fecha': fecha, 'codigo': c, 'icono': ICON(c), 'texto': DESC.get(c, 'Variable'), 'max': round(tmax), 'min': round(tmin),
                     'lluvia': pr, 'viento': round(viento), 'plan': plan})
    (ROOT / 'tiempo.json').write_text(json.dumps({'actualizado': datetime.datetime.now().isoformat(timespec='minutes'), 'fuente': 'Open-Meteo', 'dias': dias}, ensure_ascii=False), encoding='utf-8')
    print(' · '.join(f"{x['fecha'][5:]} {x['icono']} {x['max']}° {x['plan']}" for x in dias))

if __name__ == '__main__':
    main()
