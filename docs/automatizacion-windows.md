# Automatización de alertas en Windows

Las alertas de Mi Botiquín Digital se recalculan automáticamente cada vez que
alguien abre el panel. Para que también se actualicen y se envíen los correos
aunque nadie use la app, programa la ejecución periódica del comando
`sincronizar_alertas` con el **Programador de tareas de Windows**.

El proyecto incluye el script `scripts\sincronizar_alertas.ps1`, que:

- usa el entorno virtual `venv` del proyecto,
- ejecuta `python manage.py sincronizar_alertas`,
- guarda la salida y el código de salida en `logs\sincronizar_alertas.log`.

> La carpeta del proyecto en estos ejemplos es
> `C:\Users\LYZAR\Music\My botiquin`. Ajusta la ruta si la mueves.

## 1. Requisitos previos

1. El entorno virtual existe: `venv\Scripts\python.exe`.
2. El archivo `.env` tiene las credenciales de Gmail (ver `.env.example`).
   El comando lee `.env` automáticamente; no hace falta definir variables en la tarea.
3. Prueba el script a mano antes de programarlo:

   ```powershell
   cd "C:\Users\LYZAR\Music\My botiquin"
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sincronizar_alertas.ps1
   ```

   Debe terminar con `exit=0` en `logs\sincronizar_alertas.log`.

## 2. Crear la tarea (opción A: interfaz gráfica)

1. Abre el Programador de tareas (`taskschd.msc`) y elige **Crear tarea…**
   (no uses "Crear tarea básica", porque no permite todas las opciones).
2. **General**
   - Nombre: `MiBotiquin - Sincronizar alertas`.
   - Marca **Ejecutar tanto si el usuario inició sesión como si no**.
     Windows pedirá tu contraseña de usuario al guardar.
3. **Desencadenadores** → **Nuevo…**
   - Iniciar la tarea: **Según una programación**.
   - Configuración: **Diariamente**, a las 7:00 a. m.
   - En **Configuración avanzada**, marca **Repetir la tarea cada** `1 hora`
     durante **Indefinidamente**.
4. **Acciones** → **Nueva…**
   - Acción: **Iniciar un programa**.
   - Programa o script: `powershell.exe`
   - Agregar argumentos:

     ```
     -NoProfile -ExecutionPolicy Bypass -File "C:\Users\LYZAR\Music\My botiquin\scripts\sincronizar_alertas.ps1"
     ```

   - Iniciar en: `C:\Users\LYZAR\Music\My botiquin`
5. **Condiciones**: desmarca **Iniciar la tarea solo si el equipo está conectado a la corriente alterna**
   si usas un portátil que pueda estar con batería.
6. **Configuración**: marca **Si la tarea falla, reiniciarla cada** `10 minutos` (hasta 3 intentos).

## 3. Crear la tarea (opción B: línea de comandos)

Abre el **Símbolo del sistema** (`cmd`, no PowerShell: las comillas escapadas de
`/TR` solo se interpretan bien ahí) y ejecuta:

```bat
schtasks /Create /TN "MiBotiquin - Sincronizar alertas" /SC HOURLY /MO 1 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\LYZAR\Music\My botiquin\scripts\sincronizar_alertas.ps1\"" /RL LIMITED /F
```

- `/SC HOURLY /MO 1`: se ejecuta cada hora.
- `/RL LIMITED`: no requiere permisos de administrador.
- `/F`: reemplaza la tarea si ya existe.

Nota: con esta opción la tarea solo se ejecuta mientras tu sesión esté iniciada.
Para ejecutarla también con la sesión cerrada, usa la opción A (paso 2).

## 4. Probar la tarea

```powershell
schtasks /Run /TN "MiBotiquin - Sincronizar alertas"
```

Espera unos segundos y revisa `logs\sincronizar_alertas.log`. Cada ejecución añade
una línea con la fecha y `exit=0` si todo salió bien.

Para ver el estado y la última hora de ejecución:

```powershell
schtasks /Query /TN "MiBotiquin - Sincronizar alertas" /V /FO LIST
```

## 5. Quitar la tarea

```powershell
schtasks /Delete /TN "MiBotiquin - Sincronizar alertas" /F
```

## 6. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| `exit=1` y "No se encontró el entorno virtual" | No existe `venv` o la ruta cambió | Crea el entorno (`python -m venv venv`) o corrige la ruta de la tarea |
| `SMTPAuthenticationError` en el log | Contraseña de aplicación incorrecta o vencida | Genera una nueva en la cuenta de Gmail y actualiza `.env` |
| `No se pudo enviar el correo de alertas` | Sin conexión o Gmail bloqueó el envío | Revisa internet; el aviso sigue visible en la app |
| La tarea no se ejecuta | El equipo estaba apagado o suspendido | Revisa el historial en el Programador de tareas (pestaña **Historial**) |

## Notas

- Las alertas se crean una sola vez por cada cambio de estado. Ejecutar la tarea
  varias veces **no** reenvía correos repetidos.
- Los correos solo se envían a usuarios con el canal **Correo electrónico** en su perfil.
- Nunca subas `.env` al repositorio: contiene la contraseña de aplicación.
