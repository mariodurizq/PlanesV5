# Me Renta Mazo · ficha para la App Store

Todo lo que hay que pegar en App Store Connect al crear la app. Identificador de la app: `com.merentamazo.app`.

## Datos básicos

| Campo | Valor |
|---|---|
| Nombre (máx. 30) | Me Renta Mazo |
| Subtítulo (máx. 30) | Planes y sitios que rentan |
| Categoría principal | Comida y bebida |
| Categoría secundaria | Viajes |
| Clasificación por edad | 17+ (menciona bares, copas y discotecas) |
| Precio | Gratis |
| Idioma principal | Español (España) |
| URL de soporte | https://mariodurizq.github.io/PlanesV5/legal.html |
| URL de la política de privacidad | https://mariodurizq.github.io/PlanesV5/legal.html#privacidad |
| Copyright | 2026 Mario |

## Palabras clave (máx. 100 caracteres)

```
planes,madrid,restaurantes,bares,tapas,copas,brunch,rooftop,ocio,museos,cena,mapa,discotecas,sushi
```

## Texto promocional (máx. 170)

```
Dile lo que te apetece como a un amigo y te monta el plan en Madrid: sitios que rentan, horarios, mapa y paseo entre paradas.
```

## Descripción

```
Me Renta Mazo es tu guía de planes en Madrid. Escríbele lo que te apetece como se lo dirías a un amigo y te monta el plan: dónde comer, por dónde pasear, dónde tomar algo y dónde acabar la noche, con horarios, mapa y lo que se tarda entre paradas.

PÍDEME LO QUE QUIERAS
• «Pasar el día por el centro», «cena y copas en Malasaña», «plan con niños el domingo»
• «Nada de sushi, cena asiática por menos de 25 euros», «tengo 2 horas libres cerca de Sol»
• Entiende zonas, platos, presupuesto, con quién vas, si llueve y cuánto tiempo tienes
• Cada parada trae otras opciones de la zona para cambiarla con un toque

SITIOS QUE RENTAN
• Una selección propia de restaurantes, bares, coctelerías, rooftops, shishas y discotecas de Madrid
• Mapa con todos los sitios, filtros por tipo de cocina y capas de museos, mercados y discotecas
• Horarios: no te recomienda lo que está cerrado a esa hora

HECHO PARA EL IPHONE
• Te avisa una hora antes de que empiece tu plan
• Avisos opcionales con ideas para el finde
• Comparte planes por WhatsApp con la hoja de compartir de iOS
• Funciona sin conexión con tu lista y Pídeme

Sin registro, sin publicidad y sin rastreo.
```

## Notas para el revisor (App Review Information → Notes)

```
Me Renta Mazo is a curated guide and plan builder for Madrid (Spain). The app content is bundled inside the app and works offline.

Native features:
- Local notifications: in the "Pídeme" tab, type for example "cena y copas en Malasaña el sábado", tap "Pensar" and then "🔔 Avisarme antes del plan" to get a reminder one hour before the plan starts. In "Tu espacio" you can turn on a weekly "Ideas para el finde" reminder (Fridays 18:00).
- Native iOS share sheet for plans and places.
- Location (only when in use) to show places near the user. Location is never stored or sent anywhere.
- Haptic feedback, offline banner and the merentamazo:// URL scheme.

No login is required. No ads, no tracking, no in-app purchases.
The UI is in Spanish. Example requests: "pasar el día por el centro", "plan si llueve", "cena italiana o sushi".
```

## Privacidad de la app (App Store Connect → Privacidad de la app)

- **¿Recopilas datos?** Sí.
- **Datos de uso → Interacción con el producto:** no vinculados a la identidad · sin rastreo · finalidad: analítica. Es GoatCounter: recuentos anónimos sin cookies.
- **Diagnóstico → Otros datos de diagnóstico:** no vinculados · sin rastreo · finalidad: funcionalidad de la app. Son los avisos de «Reportar un error», que solo se envían si la persona los manda.
- **Ubicación:** no se recopila (se usa solo en el móvil).

## Capturas (iPhone 6,9", 1320 × 2868; al menos 3)

1. Pídeme con un plan de día completo (mapa + paradas).
2. Mapa con los sitios que rentan (tema carmesí).
3. Sitios que rentan.
4. Lista de opciones «italiano o sushi».
5. El recordatorio del plan (notificación en pantalla bloqueada).

## Pasos para publicarla

1. Darse de alta en el Apple Developer Program (99 $ al año) con tu Apple ID.
2. En App Store Connect → Usuarios y acceso → Integraciones → claves de la API de App Store Connect: crear una clave con rol «App Manager» y descargar el archivo .p8. Se descarga una sola vez.
3. En GitHub → Settings → Secrets and variables → Actions, crear 4 secretos:
   - APPSTORE_KEY_ID: el «Key ID» de la clave.
   - APPSTORE_ISSUER_ID: el «Issuer ID» que sale encima de la lista de claves.
   - APPSTORE_KEY_P8: el contenido entero del archivo .p8.
   - APPLE_TEAM_ID: el «Team ID» de developer.apple.com → Membership.
4. En App Store Connect → Apps → «+»: crear la app con el identificador `com.merentamazo.app`.
5. En GitHub → Actions → «App de iPhone» → Run workflow, con «Subir a TestFlight» marcado. En unos 15 minutos aparece en TestFlight.
6. Probarla en tu iPhone con TestFlight, rellenar esta ficha y las capturas, y enviarla a revisión.
