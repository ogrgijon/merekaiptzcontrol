"""Small runtime translation helpers for the application UI."""

from typing import Union

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QLabel,
    QMenu,
    QRadioButton,
    QPushButton,
    QWidget,
)


_SPANISH = {
    "MerekaiPTZControl - PTZ Camera Control": "MerekaiPTZControl - Control de cámara PTZ",
    "&File": "&Archivo",
    "&Settings": "&Configuración",
    "E&xit": "S&alir",
    "&Help": "A&yuda",
    "&About": "&Acerca de",
    "Add Camera": "Añadir cámara",
    "Add a camera from the available cameras list": "Añade una cámara de la lista de cámaras disponibles",
    "Device Info": "Información del dispositivo",
    "Status: Disconnected": "Estado: desconectada",
    "Status: Connected": "Estado: conectada",
    "Ready": "Listo",
    "No cameras found": "No se encontraron cámaras",
    "No new cameras available": "No hay cámaras nuevas disponibles",
    "Disconnect": "Desconectar",
    "Remove": "Quitar",
    "Connected to {camera}": "Conectado a {camera}",
    "Disconnected": "Desconectada",
    "No Camera": "Sin cámara",
    "Please connect a camera first.": "Conecta una cámara primero.",
    "Settings - MerekaiPTZControl": "Configuración - MerekaiPTZControl",
    "Motor Control": "Control del motor",
    "Motor Interval Timer (ms):": "Intervalo del motor (ms):",
    "Time between motor commands (lower = faster response, higher = smoother)": "Tiempo entre comandos del motor (menor = respuesta más rápida, mayor = más fluida)",
    "Auto-Repeat Initial Delay (ms):": "Retardo inicial de repetición (ms):",
    "Delay before auto-repeat starts when button is held": "Retardo antes de iniciar la repetición al mantener pulsado el botón",
    "Auto-Repeat Interval (ms):": "Intervalo de repetición automática (ms):",
    "Time between auto-repeat commands": "Tiempo entre comandos repetidos",
    "Use Native Motion Control": "Usar control de movimiento Nativo",
    "Use camera-specific Native motion control if available": "Usa el control de movimiento Nativo específico de la cámara si está disponible",
    "Camera Settings": "Configuración de cámara",
    "Baud Rate:": "Velocidad en baudios:",
    "Timeout (seconds):": "Tiempo de espera (segundos):",
    "Max Presets:": "Máximo de preajustes:",
    "UI Settings": "Configuración de interfaz",
    "Language:": "Idioma:",
    "Enable Keyboard Shortcuts": "Activar atajos de teclado",
    "Enable Global Hotkeys (Windows only)": "Activar teclas globales (solo Windows)",
    "OK": "Aceptar",
    "Cancel": "Cancelar",
    "Reset to Defaults": "Restablecer valores predeterminados",
    "Pan/Tilt Control": "Control de paneo/inclinación",
    "Image Controls": "Controles de imagen",
    "Zoom Control": "Control de zoom",
    "Focus Control": "Control de enfoque",
    "Iris Control": "Control del iris",
    "White Balance": "WB",
    "Exposure Control": "Control de exposición",
    "Speed:": "Velocidad:",
    "Speed": "Velocidad",
    "Zoom:": "Zoom:",
    "Zoom Position:": "Posición del zoom:",
    "Focus:": "Enfoque:",
    "Iris:": "Iris:",
    "Iris Level:": "Nivel del iris:",
    "Mode:": "Modo:",
    "Exposure:": "Exposición:",
    "Contrast:": "Contraste:",
    "Brightness": "Brillo",
    "Iris": "Iris",
    "WB": "WB",
    "Exposure": "Exposición",
    "Contrast": "Contraste",
    "Saturation": "Saturación",
    "Color intensity": "Intensidad del color",
    "Sharpness": "Nitidez",
    "Gamma": "Gamma",
    "Hue": "Tono",
    "Gain": "Ganancia",
    "Backlight": "Contraluz",
    "Auto Focus": "Enfoque automático",
    "Manual Focus": "Enfoque manual",
    "Indoor": "Interior",
    "Outdoor": "Exterior",
    "HOME": "INICIO",
    "STOP": "PARAR",
    "WIDE": "ANCHO",
    "NEAR": "CERCA",
    "FAR": "LEJOS",
    "OPEN": "ABRIR",
    "CLOSE": "CERRAR",
    "Save Preset": "Guardar preajuste",
    "Click a slot to save...": "Pulsa una posición para guardar...",
    "Activate, then click a slot to save the current camera state there": "Actívalo y pulsa una posición para guardar el estado actual de la cámara",
    "Camera position: pan (X), tilt (Y), zoom (Z); estimated when unreadable": "Posición de cámara: paneo (X), inclinación (Y), zoom (Z); estimada si no se puede leer",
    "No Camera Connected": "Ninguna cámara conectada",
    "Connect a camera first.": "Conecta una cámara primero.",
    "Preset Failed": "Error en el preajuste",
    "The camera rejected this preset.": "La cámara rechazó este preajuste.",
    "Preset Empty": "Preajuste vacío",
    "Save a software preset to this slot before recalling it.": "Guarda un preajuste de software en esta posición antes de recuperarlo.",
    "Preset {number}. Right-click to rename.": "Preajuste {number}. Haz clic derecho para cambiar el nombre.",
    "Right-click to rename.": "Haz clic derecho para cambiar el nombre.",
    "{name}. Right-click to rename.": "{name}. Haz clic derecho para cambiar el nombre.",
    "Empty": "Vacío",
    "Preset {number}": "Preajuste {number}",
    "Adjust {name}": "Ajustar {name}",
    "Adjust {name}. Right-click to rename.": "Ajustar {name}. Haz clic derecho para cambiar el nombre.",
    "Reset {name} to its default": "Restablecer {name} a su valor predeterminado",
    "Reset {name}": "Restablecer {name}",
    "Reset All Controls": "Restablecer",
    "Reset the selected setting": "Restablecer el ajuste seleccionado",
    "Change name": "Cambiar nombre",
    "Hide this setting": "Ocultar este ajuste",
    "Show this setting": "Mostrar este ajuste",
    "Adjust Pan / Tilt": "Ajustar paneo/inclinación",
    "Pan / Tilt": "Paneo / inclinación",
    "Return pan and tilt to their default center": "Centrar el paneo y la inclinación",
    "Position": "Posición",
    "Home": "Inicio",
    "Return zoom to its home wide position": "Restablecer el zoom a su posición gran angular",
    "Restore autofocus": "Restablecer el enfoque automático",
    "About MerekaiPTZControl": "Acerca de MerekaiPTZControl",
    "Professional PTZ Camera Control": "Control profesional de cámaras PTZ",
    "Close": "Cerrar",
    "Camera Information - {camera}": "Información de cámara - {camera}",
    "Camera Information": "Información de la cámara",
    "Port:": "Puerto:",
    "Status:": "Estado:",
    "Model:": "Modelo:",
    "Firmware:": "Firmware:",
    "Pan/Tilt Range": "Rango de paneo/inclinación",
    "Pan:": "Paneo:",
    "Tilt:": "Inclinación:",
    "Zoom Range": "Rango de zoom",
    "Features": "Funciones",
    "Presets:": "Preajustes:",
    "Camera {index}: {label}": "Cámara {index}: {label}",
    "Settings": "Configuración",
    "About": "Acerca de",
    "Camera Error": "Error de cámara",
    "Could not create the camera controller.": "No se pudo crear el controlador de cámara.",
    "Connection Failed": "Error de conexión",
    "Could not connect to {camera}": "No se pudo conectar con {camera}",
    "Rename Camera Setting": "Cambiar nombre del ajuste de cámara",
    "Setting name:": "Nombre del ajuste:",
    "Invalid Setting Name": "Nombre de ajuste no válido",
    "The setting name cannot be empty.": "El nombre del ajuste no puede estar vacío.",
    "Rename Preset": "Cambiar nombre del preajuste",
    "Preset name:": "Nombre del preajuste:",
    "Invalid Preset Name": "Nombre de preajuste no válido",
    "The preset name cannot be empty.": "El nombre del preajuste no puede estar vacío.",
    "Preset Recall Incomplete": "Recuperación incompleta del preajuste",
    "The camera rejected one or more position commands.": "La cámara rechazó uno o más comandos de posición.",
    "Focus": "Enfoque",
    "Zoom": "Zoom",
}

_ENGLISH = {spanish: english for english, spanish in _SPANISH.items()}


def translate(text: str, language: str = "en") -> str:
    """Translate an English UI string, leaving unknown text unchanged."""
    if language == "es":
        if text.startswith("Camera Information - "):
            return "Información de cámara - " + text[len("Camera Information - "):]
        if text.startswith("Connected to "):
            return "Conectado a " + text[len("Connected to "):]
        return _SPANISH.get(text, text)
    if language == "en":
        if text.startswith("Información de cámara - "):
            return "Camera Information - " + text[len("Información de cámara - "):]
        if text.startswith("Conectado a "):
            return "Connected to " + text[len("Conectado a "):]
        return _ENGLISH.get(text, text)
    return text


def _translate_property(
    obj: Union[QWidget, QAction], property_name: str, language: str
) -> None:
    getter_name, setter_name = {
        "toolTip": ("toolTip", "setToolTip"),
        "windowTitle": ("windowTitle", "setWindowTitle"),
        "menuTitle": ("title", "setTitle"),
    }.get(property_name, ("text", "setText"))
    getter = getattr(obj, getter_name, None)
    setter = getattr(obj, setter_name, None)
    if not callable(getter) or not callable(setter):
        return

    current = getter()
    if not current:
        return

    source_property = f"_merekai_{property_name}_source"
    translated_property = f"_merekai_{property_name}_translated"
    source = obj.property(source_property)
    previous_translation = obj.property(translated_property)
    if not isinstance(source, str) or current != previous_translation:
        source = current
        obj.setProperty(source_property, source)

    result = translate(source, language)
    setter(result)
    obj.setProperty(translated_property, result)


def apply_language(root: QWidget, language: str) -> None:
    """Translate supported text properties under a widget, preserving user text."""
    widgets = [root, *root.findChildren(QWidget)]
    text_widgets = (QCheckBox, QGroupBox, QLabel, QRadioButton, QPushButton)
    for widget in widgets:
        if isinstance(widget, text_widgets):
            _translate_property(widget, "text", language)
        _translate_property(widget, "toolTip", language)
        if widget.windowTitle():
            _translate_property(widget, "windowTitle", language)
        if isinstance(widget, QMenu):
            _translate_property(widget, "menuTitle", language)

    for action in root.findChildren(QAction):
        _translate_property(action, "text", language)
        _translate_property(action, "toolTip", language)
