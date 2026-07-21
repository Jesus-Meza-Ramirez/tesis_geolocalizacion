# incidencias/views.py

from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import date, datetime

from usuarios.models import Usuario
from incidencias.models import BoleteroCajero
from .models import Incidencia, Cliente, OrdenAtencion, Zona, CoordenadaZona, TecnicoZona
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








def punto_en_poligono(lat, lon, poligono):
    dentro = False
    j = len(poligono) - 1

    for i in range(len(poligono)):
        lat_i, lon_i = poligono[i]
        lat_j, lon_j = poligono[j]

        if ((lon_i > lon) != (lon_j > lon)):
            interseccion = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i

            if lat < interseccion:
                dentro = not dentro

        j = i

    return dentro








def registrar_orden_atencion(request):
    """
    Registra una orden de atención.
    Si el cliente no existe, lo crea.
    Si ya existe, actualiza sus datos.
    Además, asigna automáticamente técnico y zona según latitud/longitud.
    Para pruebas permite ingresar fecha y hora manual de asignación.
    """
    if request.method == "POST":
        codigo_cliente = request.POST.get("codigo_cliente", "").strip()
        nombre_cliente = request.POST.get("nombre_cliente", "").strip()
        celular = request.POST.get("celular", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        distrito = request.POST.get("distrito", "").strip()
        departamento = request.POST.get("departamento", "").strip()
        indicaciones = request.POST.get("indicaciones", "").strip()

        

        latitud = request.POST.get("latitud") or None
        longitud = request.POST.get("longitud") or None

        fecha_asignacion_final = datetime.now()

        cliente, creado = Cliente.objects.get_or_create(
            codigo_cliente=codigo_cliente,
            defaults={
                "nombre_cliente": nombre_cliente,
                "celular": celular,
                "direccion": direccion,
                "distrito": distrito,
                "departamento": departamento,
                "latitud": latitud,
                "longitud": longitud,
                "fecha_registro": timezone.now(),
                "activo": True,
            }
        )

        if not creado:
            cliente.nombre_cliente = nombre_cliente or cliente.nombre_cliente
            cliente.celular = celular or cliente.celular
            cliente.direccion = direccion or cliente.direccion
            cliente.distrito = distrito or cliente.distrito
            cliente.departamento = departamento or cliente.departamento
            cliente.latitud = latitud or cliente.latitud
            cliente.longitud = longitud or cliente.longitud
            cliente.save()

        tecnico_asignado = None
        zona_asignada = None

        if latitud and longitud:
            lat_cliente = float(latitud)
            lon_cliente = float(longitud)

            zonas_coincidentes = []

            zonas = Zona.objects.filter(activo=True)

            for zona in zonas:
                puntos = CoordenadaZona.objects.filter(
                    id_zona=zona
                ).order_by("orden_punto")

                poligono = [
                    (float(p.latitud), float(p.longitud))
                    for p in puntos
                ]

                if len(poligono) >= 3 and punto_en_poligono(lat_cliente, lon_cliente, poligono):
                    zonas_coincidentes.append(zona)

            turno_actual = obtener_turno_por_fecha(fecha_asignacion_final)

            if zonas_coincidentes and turno_actual:
                asignaciones = (
                    TecnicoZona.objects
                    .select_related("id_tecnico", "id_zona")
                    .filter(
                        id_zona__in=zonas_coincidentes,
                        id_tecnico__turno=turno_actual,
                        activo=True
                    )
                )

                mejor_asignacion = None
                menor_carga = None

                for asignacion in asignaciones:
                    tecnico = asignacion.id_tecnico

                    pendientes = OrdenAtencion.objects.filter(
                        id_tecnico=tecnico,
                        estado="por_atender"
                    ).count()

                    if menor_carga is None or pendientes < menor_carga:
                        menor_carga = pendientes
                        mejor_asignacion = asignacion

                if mejor_asignacion:
                    tecnico_asignado = mejor_asignacion.id_tecnico
                    zona_asignada = mejor_asignacion.id_zona
                else:
                    zona_asignada = zonas_coincidentes[0]

        OrdenAtencion.objects.create(
            id_cliente=cliente,
            id_tecnico=tecnico_asignado,
            id_zona=zona_asignada,
            estado="por_atender",
            indicaciones=indicaciones,
            fecha_asignacion=fecha_asignacion_final
        )

        return redirect("panel_control_interno")


def obtener_turno_por_fecha(fecha_hora):
    hora = fecha_hora.hour

    # 22:00 hasta 13:59 -> turno mañana
    if hora >= 22 or hora < 14:
        return "mañana"

    # 14:00 hasta 21:59 -> turno tarde
    return "tarde"










