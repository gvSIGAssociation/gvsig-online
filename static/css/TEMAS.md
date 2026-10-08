# Temas (skins) del panel de administración

Cómo dar de alta y modificar un tema de gvSIG Online.

El resumen es: **se edita un solo fichero, `gol-themes.css`, añadiendo un bloque de
nueve variables**. Ya no se crean hojas de estilo por tema.

---

## Arquitectura

Cuatro hojas, con responsabilidades separadas. Se cargan en este orden desde
`base.html`, `base_compress.html`, `base_symbology.html` y
`base_symbology_compress.html`:

| Fichero | Responsabilidad |
|---|---|
| `gol-tokens.css` | Tokens de diseño comunes: radios, sombras, transiciones y alias `--pf-*`, `--pl-*`, `--h-*` |
| `gol-themes.css` | **Única fuente de verdad del color de cada tema.** Solo declara variables |
| `gol-skin-base.css` | Reglas de tema sobre AdminLTE 2, escritas una vez y resueltas con variables |
| `gol-layout.css` | Cabecera, menú lateral, contenido y pie. Genérico: no nombra ningún tema |

La clase del tema la pone `GVSIGOL_SKIN` en el `<body>`:

```html
<body class="hold-transition {{GVSIGOL_SKIN}} sidebar-mini">
```

`gol-skin-base.css` y `gol-layout.css` usan el prefijo `body[class*="skin-"]`, que
reproduce el ámbito que tenían los antiguos selectores `.skin-<nombre>`: las reglas
solo se aplican si el `<body>` lleva una clase de tema. Las páginas sin tema
(`select_public_*`, `ogc_services`, `services_view` y las portadas de apps que ponen
la clase en un elemento interno) quedan intactas.

No existe ningún registro de temas en código Python. `GVSIGOL_SKIN` se pasa por el
context processor y se escribe tal cual como clase, así que no hay lista cerrada que
validar: si el tema no tiene bloque en `gol-themes.css`, se queda con la paleta por
defecto (la de `skin-blue`) en lugar de fallar.

---

## Dar de alta un tema nuevo

### 1. Añadir el bloque de paleta

En `gol-themes.css`, al final de la sección `TEMAS DE FONDO OSCURO`:

```css
.skin-miayuntamiento {
	--hdr-bg:        #009681;
	--hdr-bg-dk:     #007A68;
	--sb-bg:         #0f2420;
	--sb-bg-dark:    #0a1a17;
	--sb-accent:     #009681;
	--sb-accent-lt:  #4db8a8;
	--gol-accent:    #009681;
	--gol-accent-dk: #007A68;
	--gol-accent-lt: rgba(0,150,129,0.06);
}
```

Con esas nueve variables el tema queda completo. Todo lo demás (textos, bordes,
sombras, transiciones, campos de la cabecera) sale de los valores por defecto y no
hace falta declararlo.

Criterio de color habitual:

- `--hdr-bg` es el color corporativo y `--hdr-bg-dk` una versión más oscura (un 15-20 % menos de luminosidad).
- `--sb-bg` y `--sb-bg-dark` son tonos muy oscuros de la misma familia cromática, para que el sidebar no desentone con la cabecera.
- `--sb-accent` suele coincidir con el color corporativo. `--sb-accent-lt` es su versión aclarada **en los temas oscuros**; en los claros tiene que ser al contrario, una versión más oscura, porque es el color con el que se pinta el texto y los iconos del elemento activo y el fondo de la píldora es claro. Comparar `.skin-blue` (`#4a7fa5` con `-lt` `#7eb8d4`) con `.skin-blue-light` (`#3c8dbc` con `-lt` `#1b7baa`).
- Los tres `--gol-accent*` replican el acento para el contenido. El `-lt` es el mismo color en `rgba()` con alfa `0.06`.

### 2. Solo si el tema es de fondo claro

Añadir además su nombre a la lista de polaridad clara que hay en la sección
`TEMAS DE FONDO CLARO`:

```css
.skin-blue-light,
.skin-black-light,
.skin-miayuntamiento-light,   /* <-- aquí */
...
.skin-yellow-light {
```

Esa lista invierte el comportamiento del sidebar: sombras más suaves, hover oscuro
sobre fondo claro en vez de blanco translúcido, y desplegables del modo colapsado
claros. El elemento activo no cambia, porque la píldora tintada con el acento
funciona igual en las dos polaridades.

El sufijo `-light` es **convención, no requisito**: lo que determina la polaridad es
estar en esa lista, no cómo se llame el tema. `skin-elegant` es un tema claro sin
sufijo. Si eliges un nombre así, deja un comentario en la lista para que nadie lo
quite pensando que está fuera de sitio.

El bloque de paleta de un tema claro va **después** de esa lista en el fichero. Los
dos selectores tienen la misma especificidad, así que es el orden lo que permite al
tema redefinir cualquiera de las variables que la lista declara.

Los temas claros declaran además `--sb-text`, `--sb-text-muted` y `--sb-border` en su
bloque de paleta, porque los textos por defecto están pensados para fondo oscuro.
Ver `.skin-blue-light` o `.skin-elegant` como referencia.

### 3. Documentarlo

Añadir el nombre a los comentarios de temas disponibles de `.env.template` y de
`gvsigol/settings_tpl.py`. Es solo documentación para quien configure el despliegue.

### 4. Activarlo

En el `.env` del despliegue:

```
GVSIGOL_SKIN="skin-miayuntamiento"
```

---

## Modificar un tema existente

Cambiar los valores de su bloque en `gol-themes.css`. Nada más: el cambio se propaga
a la cabecera, el sidebar, los botones, las cajas, la paginación y los formularios,
porque todas las reglas consumen esas variables.

---

## Referencia de variables

### Cabecera

| Variable | Afecta a |
|---|---|
| `--hdr-bg` | fondo de la barra de cabecera, logo incluido |
| `--hdr-bg-dk` | hover del toggle del sidebar y tono oscuro del degradado del menú de usuario |
| `--hdr-text` | color del texto e iconos |
| `--hdr-text-dim` | texto en hover y estado activo |
| `--hdr-item-hover` | fondo de los elementos al pasar el ratón |
| `--hdr-border` | borde inferior de la cabecera |
| `--hdr-shadow` | sombra de la cabecera |
| `--hdr-logo-bg` | fondo del recuadro del logo |
| `--hdr-logo-border` | separador vertical entre logo y navbar |
| `--hdr-logo-filter` | filtro CSS sobre la imagen del logo, en sus dos tamaños |
| `--hdr-field-bg` | fondo del selector de idioma y buscadores |
| `--hdr-field-bg-focus` | ídem con el foco puesto |
| `--hdr-field-border` | borde de esos campos |
| `--hdr-field-border-focus` | ídem con el foco puesto |
| `--hdr-field-text` | texto de esos campos |
| `--hdr-user-img-border` | borde del avatar del menú de usuario |

### Sidebar

| Variable | Afecta a |
|---|---|
| `--sb-bg` | fondo del menú lateral |
| `--sb-bg-dark` | submenús, cabeceras de sección y desplegables del modo colapsado |
| `--sb-accent` | color de acento: tinte e iconos del elemento activo |
| `--sb-accent-lt` | texto e iconos del elemento activo |
| `--sb-text` | texto de los elementos |
| `--sb-text-muted` | texto secundario y cabeceras de sección |
| `--sb-border` | separadores |
| `--sb-shadow` | sombra del borde derecho |
| `--sb-user-text` | texto del panel de usuario |
| `--sb-item-hover` | fondo del elemento al pasar el ratón |
| `--sb-item-hover-text` | texto en hover |
| `--sb-sub-hover-bg` | fondo de los subelementos en hover |
| `--sb-sub-hover-text` | texto de los subelementos en hover |
| `--sb-sub-active-bg` | fondo del subelemento activo |
| `--sb-flyout-text` | texto de los desplegables del modo colapsado |
| `--sb-flyout-shadow` | sombra de esos desplegables |
| `--sb-transition` | duración de las transiciones |

### Contenido

| Variable | Afecta a |
|---|---|
| `--gol-accent` | botones primarios, cajas, paginación, pestañas y formularios |
| `--gol-accent-dk` | hover y bordes de ese acento |
| `--gol-accent-lt` | fondos tenues del acento |

`gol-tokens.css` reexpone estos tres como alias `--pf-*` (formularios), `--pl-*`
(listados) y `--h-*` (portada), para que las plantillas que todavía declaran su
propio `:root` sigan funcionando sin cambios.

### Tokens derivados

Se calculan en el bloque `body` de `gol-themes.css` a partir de la paleta, así que no
hace falta declararlos, pero cualquier tema puede redefinirlos porque su selector
`.skin-<nombre>` gana al de `body`:

| Variable | Se deriva de |
|---|---|
| `--hdr-logo-bg` | `--hdr-bg` |
| `--hdr-logo-bg-hover` | `--hdr-bg-dk` |
| `--hdr-field-option-bg` | `--hdr-bg-dk` |
| `--hdr-usermenu-bg` | degradado de `--hdr-bg` a `--hdr-bg-dk` |
| `--sb-item-active-bg` | `--sb-accent` al 22 % con `color-mix()` |
| `--sb-item-active-text` | `--sb-accent-lt` |
| `--sb-item-active-border` | `--sb-accent-lt` |
| `--sb-flyout-bg` | `--sb-bg-dark` |

El tinte de `--sb-item-active-bg` se calcula con `color-mix()`, que la hoja da por
soportado igual que el resto del CSS del panel. Si alguna vez hiciera falta un
respaldo, hay que escribirlo en la propiedad final y no aquí: una custom property
acepta casi cualquier cosa al parsear, así que una segunda declaración gana siempre y
el fallo de `color-mix()` solo aparece al sustituirla, momento en el que la propiedad
toma su valor inicial en lugar de la declaración anterior.

Van en `body` y no en `:root` a propósito: un `var()` dentro de una custom property se
sustituye en el elemento donde se declara, y la clase del tema está en el `<body>`.
Declarados en `:root` se resolverían siempre contra los valores por defecto.

---

## Casos especiales

### Cabecera clara con texto oscuro

El comportamiento por defecto es cabecera de color con texto blanco. Un tema que
necesite cabecera clara tiene que redefinir además los `--hdr-text*`,
`--hdr-item-hover`, `--hdr-border`, `--hdr-shadow` y los `--hdr-field-*`.
`.skin-black` es el único caso y sirve de ejemplo completo.

### Logo que necesita otro tratamiento

Si el cliente entrega el logotipo en color y hace falta verlo en blanco sobre la
cabecera, se usa `--hdr-logo-filter` en lugar de escribir una regla con el nombre del
tema:

```css
.skin-picanya {
	/* ... paleta ... */
	--hdr-logo-filter: brightness(0) invert(1);
}
```

El filtro se aplica a la imagen del logo en sus dos tamaños, el de la cabecera
desplegada y el del sidebar colapsado, que son el mismo fichero repetido en dos
`<span>`. Tratarlos distinto haría que el logo cambiase de aspecto al colapsar.

Esta es la pauta general para cualquier excepción: **si algo depende del tema, se
convierte en variable**; nunca se añade un selector `.skin-<nombre>` a
`gol-layout.css` ni a `gol-skin-base.css`.

---

## Qué no hacer

- No crear hojas `skins/skin-<nombre>.css`. El sistema por hoja-por-tema se eliminó.
- No tocar `skins/_all-skins.css` ni `skins/_all-skins.min.css`. Son shims de
  compatibilidad que solo importan `gol-themes.css` y `gol-skin-base.css`; los cargan
  48 plantillas de portadas de apps y de plugins, y se mantienen para no tener que
  modificar esos repositorios. Heredan los temas nuevos automáticamente.
- No añadir selectores con nombre de tema a `gol-layout.css` ni a `gol-skin-base.css`.
- No usar `!important`. Hacía falta cuando competían varias hojas de skins; ahora no
  hay con quién competir.

---

## Cómo probarlo

1. Poner `GVSIGOL_SKIN="skin-<nombre>"` en el `.env` y reiniciar.
2. Abrir el panel con recarga forzada (`Ctrl+Shift+R`), porque el navegador cachea el CSS.
3. Revisar cabecera, sidebar desplegado, sidebar colapsado (los desplegables flotantes
   usan variables propias), menú de usuario, un listado y un formulario.
4. Revisar también la portada de alguna app de `restricted/`, que carga el shim
   `_all-skins.css` en lugar de las hojas directamente.

En despliegue hace falta `collectstatic`. Si se han borrado ficheros, usar
`collectstatic --clear`, porque las copias ya recogidas en `STATIC_ROOT` no se
eliminan solas.
