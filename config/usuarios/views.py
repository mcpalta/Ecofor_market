from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
import logging

from .forms import RegistroForm
from .decoradores import admin_required


logger = logging.getLogger(__name__)

def registrar(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                # Guardado seguro: si el modelo lanza ValueError (RUT inválido) lo atrapamos
                usuario = form.save(commit=False)

                # seguridad adicional: impedir asignar roles privilegiados desde el form
                if getattr(usuario, "tipo_cliente", None) in ("admin", "atencion_cliente"):
                    return HttpResponseForbidden("No puedes asignar ese tipo de usuario.")

                # Si tu form no hace hashing automáticamente, form.save() lo hará porque heredamos UserCreationForm.
                usuario.save()

                # Para campos M2M (si los hubiese)
                try:
                    form.save_m2m()
                except Exception:
                    pass

                messages.success(request, "Cuenta creada correctamente. Ahora puedes iniciar sesión.")
                return redirect("login")

            except ValueError as ve:
                # tu modelo lanza ValueError("El RUT ingresado no es válido.")
                # lo mostramos como error ligado al campo 'rut'
                form.add_error("rut", str(ve))
                return render(request, "usuarios/registrar.html", {"form": form})

            except IntegrityError as ie:
                # por ejemplo si rut o username ya existe
                logger.exception("IntegrityError al crear usuario")
                form.add_error(None, "Ya existe una cuenta con esos datos. Revisa el usuario o RUT.")
                return render(request, "usuarios/registrar.html", {"form": form})

            except Exception as e:
                logger.exception("Error inesperado creando usuario")
                messages.error(request, "Ocurrió un error al crear la cuenta. Intenta nuevamente.")
                return render(request, "usuarios/registrar.html", {"form": form})
        else:
            # formulario inválido, mostrar errores
            return render(request, "usuarios/registrar.html", {"form": form})
    else:
        form = RegistroForm()
        return render(request, "usuarios/registrar.html", {"form": form})

@login_required
def dashboard(request):
    usuario = request.user
    return render(request, "usuarios/dashboard.html", {"usuario": usuario})

@admin_required
def admin_panel(request):
    return render(request, "usuarios/admin_panel.html")

def logout_view(request):
    logout(request)
    return redirect("login")
