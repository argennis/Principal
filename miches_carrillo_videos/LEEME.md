# Videos de Miches Carrillo

Código para generar los dos videos verticales (1080×1920, 30 fps, sin audio):

- **Miches_Carrillo_promo.mp4**: promocional de 15 s con los vasos de fruta.
- **Miches_Carrillo_como_llegar.mp4**: video de unos 18 s: abre con el gancho "ANTOJO de una miche" y luego muestra en el mapa la dirección, las referencias y las rutas a la sucursal.

Los videos no se hacen con inteligencia artificial: el código dibuja cada cuadro (con Pillow) y ffmpeg los une en el MP4.

## Requisitos

- Python 3.9 o más reciente
- Pillow: `pip install pillow`
- ffmpeg instalado y disponible en la terminal

## Cómo generarlos

Abre una terminal en esta carpeta y corre:

```
python3 generar.py vista          # imágenes de vista previa (unos segundos)
python3 generar.py promo          # solo el promocional
python3 generar.py como_llegar    # solo el video de cómo llegar
python3 generar.py todo           # los dos
```

Revisa primero la vista previa (`vista_previa_*.jpg`) después de cada cambio; generar el video completo tarda unos minutos.

## Qué archivo editar

| Quiero cambiar… | Archivo | Dónde |
|---|---|---|
| Colores de marca | `video_promo.py` | `RED`, `DARK`, `YEL` al inicio |
| Textos del promocional | `video_promo.py` | funciones `scene1` a `scene4` |
| Ingredientes en las etiquetas | `video_promo.py` | lista `TAGS` |
| Duración de cada escena | `video_promo.py` | lista `SCENES` (segundos) |
| Dirección y referencias (Penalty, Bar El Tropi) | `video_como_llegar.py` | `DIRECCION`, `COLONIA`, `REFERENCIAS` al inicio de las rutas |
| Rutas, pasos y títulos del mapa | `video_como_llegar.py` | lista `ROUTES` (cada paso lleva su flecha: `recto`, `der` o `izq`) |
| Duración de cada parte | `video_como_llegar.py` | `HOOK`, `OV`, `RT`, `OUT` |
| Ubicación del pin | `video_como_llegar.py` | `PIN` |
| Calles del mapa | `video_como_llegar.py` | listas `AVM_SB`, `PRIS`, etc. (coordenadas tomadas de la captura de Google Maps) |
| Calles sin salida | `video_como_llegar.py` | lista `SIN_SALIDA` |
| Tarjeta final "Te esperamos" | `video_como_llegar.py` | función `tarjeta_final` |
| Gancho inicial "ANTOJO de una miche" (primeros 2.3 s) | `gancho.py` | función `cuadro`; duración en `DURACION` |
| Sacudidas del pin y del logo final | `video_como_llegar.py` | `MAPA_GOLPES` |

Las calles que terminan sueltas se alargan solas hasta la calle más cercana o el borde del mapa, para que no se vean cortadas. Si una calle de verdad no tiene salida, agrégala a `SIN_SALIDA`.

Cada ruta en `ROUTES` tiene sus puntos (`pts`) y sus pasos: el número junto a cada paso es el punto de la ruta donde aparece esa tarjeta.

## Recursos (carpeta `recursos`)

- `logo.png`, `monograma.png`, `mascota.png`: tus archivos con el fondo blanco quitado.
- `vasos_fruta.png`: los vasos recortados de tu cartel.
- `Baileywick-del-manual.cff`: tu tipografía, extraída del manual de marca. **Solo trae las letras y números del manual, sin acentos ni signos**; por eso los textos con esta letra van sin acentos. Si tienes el archivo completo de la fuente (con su licencia), cámbialo en `FONT` dentro de `video_promo.py`.
- `InterDisplay-Black.otf`: tipografía libre (licencia OFL) para nombres de calles y pasos, porque sí tiene acentos.

## Cómo funciona por dentro

- `video_promo.py`: colores, tipografía, recursos y funciones compartidas (texto, fondos con zigzag, sombras), más las 4 escenas del promocional.
- `mapa_comun.py`: piezas del mapa que se reutilizan (pin con el monograma, tarjetas de pasos, títulos, intro con la mascota).
- `video_como_llegar.py`: el mapa calcado de la captura, las rutas, la cámara y la escena final.
- `gancho.py`: el inicio "ANTOJO de una miche". El video de cómo llegar lo usa como primera parte; también se puede generar solo con `python3 gancho.py` (o `python3 gancho.py vista`).
- `generar.py`: genera cada parte en paralelo y las une sin volver a codificar.
