# usuarios/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Usuario, limpiar_rut, validar_rut

class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ["username", "email", "rut", "tipo_cliente", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Roles que NO se pueden asignar desde el registro público
        ROLES_PROHIBIDOS = ("admin", "atencion_cliente")

        # Filtrar choices de tipo_cliente para que no aparezcan roles prohibidos
        self.fields["tipo_cliente"].choices = [
            (value, label) for value, label in self.fields["tipo_cliente"].choices
            if value not in ROLES_PROHIBIDOS
        ]

    def clean_rut(self):
        """
        Normaliza y valida el RUT. Acepta formatos:
          - 12.345.678-5
          - 12345678-5
          - 123456785  (sin guion; se toma el último caracter como DV)
        Devuelve el RUT en el formato que use tu modelo (limpio: sin puntos, con guion o sin guion
        según tu preferencia). Aquí devolvemos el resultado de limpiar_rut().
        """
        rut_raw = self.cleaned_data.get("rut", "")
        if not rut_raw:
            # Si no quieres permitir rut vacío, lanzar ValidationError aquí:
            # raise ValidationError("El RUT es obligatorio.")
            return rut_raw

        # Eliminar espacios y mayúsculas tempranamente
        rut_sin_espacios = rut_raw.strip()

        # Si ingresaron el RUT sin guion, se asume que el último carácter es el DV
        if "-" not in rut_sin_espacios:
            # eliminar puntos y espacios para obtener solo dígitos+DV
            temp = rut_sin_espacios.replace(".", "").replace(" ", "")
            if len(temp) < 2:
                raise ValidationError("Ingrese un RUT válido (por ejemplo 12.345.678-5).")
            numero = temp[:-1]
            dv = temp[-1]
            rut_formateado = f"{numero}-{dv}"
        else:
            rut_formateado = rut_sin_espacios

        # Normalizar con la función del modelo (quita puntos, espacios y uppercase)
        rut_norm = limpiar_rut(rut_formateado)

        # validar con la función existente (devuelve True/False)
        if not validar_rut(rut_norm):
            raise ValidationError("Ingrese un RUT válido (ej: 12.345.678-5).")

        # Devuelve el RUT normalizado (tu modelo hace otra limpieza antes de save, está bien)
        return rut_norm
