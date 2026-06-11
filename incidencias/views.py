# incidencias/views.py

from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import date

from usuarios.models import Usuario
from incidencias.models import BoleteroCajero
from .models import Incidencia, Cliente, OrdenAtencion
import pytz

peru_tz = pytz.timezone("America/Lima")

def registrar_incidencia(request):
    """
    Registra una incidencia desde el modal del panel de Control Interno.
    """
    if request.method == "POST":
        # Campos que vienen del formulario
        id_bc = request.POST.get("id_bc")            # select de boletero
        estado = request.POST.get("estado")          # Conforme / Observación
        motivo = request.POST.get("motivo","") or ""        # texto
        evidencia = request.FILES.get("evidencia")   # archivo (opcional)
        fecha_str = request.POST.get("fecha_incidencia")  # YYYY-MM-DD

        # Usuario logueado (control interno)
        uid = request.session.get("uid")
        user = Usuario.objects.filter(pk=uid).first()

        # Fecha de incidencia: la que selecciona el usuario
        #    si por alguna razón viene vacía, uso la fecha de hoy
        try:
            if fecha_str:
                año, mes, día = map(int, fecha_str.split("-"))
                fecha_incidencia = date(año, mes, día)
            else:
                fecha_incidencia = timezone.now().date()
        except ValueError:
            fecha_incidencia = timezone.now().date()

        # Crear incidencia
        Incidencia.objects.create(
            id_bc_id=id_bc,
            id_usuario=user,
            fecha_incidencia=fecha_incidencia,
            motivo=motivo,
            estado=estado,
            evidencia=evidencia,
            # estos dos se llenan solos con la fecha actual
            fecha_revision=timezone.now().astimezone(peru_tz).date(),
        )

        # 5. Volver al panel para ver la tabla actualizada
        return redirect("panel_control_interno")

    # Si alguien entra por GET directo a /incidencias/registrar/
    boleteros = BoleteroCajero.objects.all()
    return render(request, "incidencias/registrar.html", {"boleteros": boleteros})





def registrar_orden_atencion(request):
    """
    Registra una orden de atención.
    Si el cliente no existe, lo crea.
    Si ya existe, reutiliza sus datos.
    """
    if request.method == "POST":
        codigo_cliente = request.POST.get("codigo_cliente", "").strip()
        nombre_cliente = request.POST.get("nombre_cliente", "").strip()
        celular = request.POST.get("celular", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        distrito = request.POST.get("distrito", "").strip()
        indicaciones = request.POST.get("indicaciones", "").strip()

        uid = request.session.get("uid")
        coordinador = Usuario.objects.filter(pk=uid).first()

        cliente, creado = Cliente.objects.get_or_create(
            codigo_cliente=codigo_cliente,
            defaults={
                "nombre_cliente": nombre_cliente,
                "celular": celular,
                "direccion": direccion,
                "distrito": distrito,
                "fecha_registro": timezone.now(),
                "activo": True,
            }
        )

        if not creado:
            cliente.nombre_cliente = nombre_cliente or cliente.nombre_cliente
            cliente.celular = celular or cliente.celular
            cliente.direccion = direccion or cliente.direccion
            cliente.distrito = distrito or cliente.distrito
            cliente.save()

        OrdenAtencion.objects.create(
            id_cliente=cliente,
            estado="por_atender",
            indicaciones=indicaciones,
            fecha_asignacion=timezone.now()
        )

        return redirect("panel_control_interno")

