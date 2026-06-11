# webui/views.py
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from usuarios.models import Usuario
from incidencias.models import Incidencia, OrdenAtencion, Tecnico  # <- tu modelo de incidencias (ajusta import si cambia)
from django.db.models import Q, Count, Case, When, IntegerField

from datetime import date
from django.core.paginator import Paginator, EmptyPage

from incidencias.models import Terminal


from django.utils import timezone
from django.urls import reverse

from incidencias.models import BoleteroCajero, Terminal

import io
from django.http import HttpResponse
from openpyxl import Workbook
from django.db.models import Q


def _require_session(request):
    """Redirect to login si no hay sesión."""
    if not request.session.get('uid'):
        return redirect('login')
    return None

@require_http_methods(["GET", "POST"])
def login_view(request):
    # 🚫 SOLO redirigimos a home si es GET y ya hay sesión
    if request.method == "GET" and request.session.get('uid'):
        return redirect('home')

    if request.method == "POST":
        usuario = (request.POST.get('usuario') or '').strip()
        contrasena = (request.POST.get('contrasena') or '').strip()

        user = Usuario.objects.filter(
            usuario_login__iexact=usuario,
            contrasena=contrasena
        ).first()

        if not user:
            messages.error(request, "Usuario o contraseña incorrectos.")
        else:
            # Opcional pero recomendable: limpiar sesión anterior
            request.session.flush()

            request.session['uid']      = user.id_usuario
            request.session['nombre']   = user.nombre
            request.session['rol']      = user.rol
            request.session['terminal'] = user.id_terminal_id  # puede ser None

            return redirect('home')

    # Si es GET sin sesión, o POST con error → mostrar login
    return render(request, 'login_full.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


def dashboard_redirect(request):
    # Si no hay sesión → login
    if not request.session.get('uid'):
        return redirect('login')

    rol = (request.session.get('rol') or '').lower()

    # 👉 ahora sí, si es control interno lo mandamos a TU panel
    if rol == 'control_interno':
        return redirect('panel_control_interno')

    # Ajusta estos destinos cuando implementes los otros paneles:
    if rol in ('admin_terminal', 'terminal'):
        return redirect('panel_admin_terminal')   # de momento lo mandamos a un placeholder
    if rol in ('admin_sistema', 'admin'):
        return redirect('panel_admin_sistema')    # placeholder

    # por defecto
    return redirect('panel_control_interno')



# ============================
#  PANEL CONTROL INTERNO (UI)
# ============================
# pega esto reemplazando la función panel_control_interno existente
def panel_control_interno(request):
    maybe_redirect = _require_session(request)
    if maybe_redirect:
        return maybe_redirect

    # ==========================
    # Base Query: órdenes de atención
    # ==========================
    qs = (
        OrdenAtencion.objects
        .select_related("id_cliente", "id_tecnico", "id_zona")
        .order_by("-fecha_asignacion", "-id_orden")
    )

    # ==========================
    # LIMIT TOP 100
    # ==========================
    qs = qs[:100]

    # ==========================
    # Paginación
    # ==========================
    paginator = Paginator(qs, 20)
    page_num = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_num)
    except:
        page_obj = paginator.page(1)

    # ==========================
    # Construcción de tabla rows
    # ==========================
    rows = []

    for orden in page_obj.object_list:
        cliente = orden.id_cliente
        tecnico = orden.id_tecnico

        rows.append({
            "id_orden": orden.id_orden,
            "fecha_asignacion": orden.fecha_asignacion,
            "codigo_cliente": cliente.codigo_cliente if cliente else "—",
            "cliente": cliente.nombre_cliente if cliente else "—",
            "celular": cliente.celular if cliente else "—",
            "direccion": cliente.direccion if cliente else "—",
            "distrito": cliente.distrito if cliente else "—",
            "tecnico": tecnico.nombre if tecnico else "Sin asignar",
            "estado": orden.estado,
            "indicaciones": orden.indicaciones or "—",
            "observacion_tecnico": orden.observacion_tecnico or "—",
            "fecha_atencion": orden.fecha_atencion,
        })

    context = {
        "usuario_nombre": request.session.get("nombre", "Usuario"),
        "terminal_actual": request.session.get("terminal") or "—",

        "rows": rows,
        "page_obj": page_obj,
        "preserved": "",

        "f1": "",
        "f2": "",
        "r1": "",
        "r2": "",
        "terminal_selected": "",
        "estado": "",
        "usuario": "",
        "motivo": "",
        "ci": "",

        "usuarios_ci": Usuario.objects.filter(rol="control_interno").order_by("nombre"),
        "boleteros": BoleteroCajero.objects.filter(estado="activo").order_by("usuario"),
        "terminales": Terminal.objects.all().order_by("id_terminal"),
        "control_internos": Usuario.objects.filter(rol="control_interno"),
    }

    return render(request, "control_interno_dashboard.html", context)



# ============================
#  PLACEHOLDERS (puedes cambiar luego)
# ============================
#def panel_admin_terminal(request):
 #   maybe_redirect = _require_session(request)
 #   if maybe_redirect: 
 #       return maybe_redirect
 #   return render(request, 'placeholder.html', {'titulo': 'Panel Admin Terminal'})

def panel_admin_terminal(request):
    # 1) Verificar sesión
    maybe_redirect = _require_session(request)
    if maybe_redirect:
        return maybe_redirect

    # 2) Obtener usuario logueado y su terminal
    uid = request.session.get('uid')
    user = (
        Usuario.objects
        .select_related('id_terminal')
        .filter(pk=uid)
        .first()
    )

    terminal_id = None
    terminal_name = '—'

    if user and user.id_terminal_id:
        terminal_id = user.id_terminal_id
        terminal_name = getattr(user.id_terminal, 'nombre_terminal', str(user.id_terminal_id))

    # ==========================================================
    # 3) Filtros (igual que Control Interno)
    #    Fecha de incidencia: f1, f2
    #    Fecha de revisión:  r1, r2
    # ==========================================================
    f1 = (request.GET.get('f1') or '').strip()  # YYYY-MM-DD
    f2 = (request.GET.get('f2') or '').strip()
    r1 = (request.GET.get('r1') or '').strip()
    r2 = (request.GET.get('r2') or '').strip()

    # 4) Query base: incidencias SOLO del terminal del usuario
    qs = (
        Incidencia.objects
        .select_related('id_bc', 'id_usuario', 'id_bc__id_terminal')
        .order_by('-fecha_revision', '-id_incidencia')
    )

    if terminal_id is not None:
        qs = qs.filter(id_bc__id_terminal_id=terminal_id)

    # =========================
    # 5) Aplicar filtros fechas
    # =========================
    # ---- Fecha de incidencia ----
    try:
        if f1:
            d1 = date.fromisoformat(f1)
            # si fecha_incidencia es DateField:
            qs = qs.filter(fecha_incidencia__gte=d1)
        if f2:
            d2 = date.fromisoformat(f2)
            qs = qs.filter(fecha_incidencia__lte=d2)
    except ValueError:
        pass

    # ---- Fecha de revisión ---- (normalmente DateTimeField)
    try:
        if r1:
            rd1 = date.fromisoformat(r1)
            qs = qs.filter(fecha_revision__gte=rd1)
        if r2:
            rd2 = date.fromisoformat(r2)
            qs = qs.filter(fecha_revision__lte=rd2)
    except ValueError:
        pass

    # 👉 Query para tarjetas (ya incluye filtros de fecha y terminal)
    qs_for_cards = qs

    # 6) Filtro por estado vía cards
    estado_card = (request.GET.get('estado_card') or '').lower()
    if estado_card in ('conforme', 'observado', 'pendiente', 'resuelto'):
        qs = qs.filter(estado__iexact=estado_card)

    # 7) Paginación
    per_page = 20
    paginator = Paginator(qs, per_page)

    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1

    try:
        page_obj = paginator.page(page_num)
    except EmptyPage:
        page_obj = paginator.page(1)

    # 8) Construcción de filas para la tabla
    rows = []
    for inc in page_obj.object_list:
        inc_id = getattr(inc, 'id_incidencia', None)

        # Fecha de incidencia (usa el campo real)
        fecha_incidencia = getattr(inc, 'fecha_incidencia', None)

        bc = getattr(inc, 'id_bc', None)
        bc_nombre = getattr(bc, 'nombre', '—') if bc else '—'
        bc_usuario = getattr(bc, 'usuario', '—') if bc else '—'
        bc_cargo = getattr(bc, 'cargo', '—') if bc else '—'

        term_obj = getattr(bc, 'id_terminal', None) if bc else None
        terminal_txt = getattr(term_obj, 'nombre_terminal', None) if term_obj else None
        if not terminal_txt:
            terminal_txt = '—'

        ci_obj = getattr(inc, 'id_usuario', None)
        control_interno = getattr(ci_obj, 'nombre', '—') if ci_obj else '—'

        estado_raw = (getattr(inc, 'estado', '') or '').lower()
        if estado_raw == 'observado':
            estado = 'Observado'
        elif estado_raw == 'pendiente':
            estado = 'Pendiente'
        elif estado_raw == 'resuelto':
            estado = 'Resuelto'
        else:
            estado = 'Conforme'

        motivo = getattr(inc, 'motivo', '—')

        evidencia_val = getattr(inc, 'evidencia', None)
        evidencia = evidencia_val.url if evidencia_val else ''

        fecha_revision = getattr(inc, 'fecha_revision', None)

        rows.append({
            'id_incidencia': inc_id,
            'fecha_incidencia': fecha_incidencia,
            'nombre': bc_nombre,
            'usuario': bc_usuario,
            'cargo': bc_cargo,
            'terminal': terminal_txt,
            'control_interno': control_interno,
            'estado': estado,
            'estado_raw': estado_raw,
            'motivo': motivo,
            'evidencia': evidencia,
            'fecha_revision': fecha_revision,
        })

    # 9) Tarjetas
    cards = {
        'activas': qs_for_cards.exclude(estado__iexact='resuelto').count(),
        'pendientes': qs_for_cards.filter(estado__iexact='pendiente').count(),
        'resueltas': qs_for_cards.filter(estado__iexact='resuelto').count(),
        'conformes': qs_for_cards.filter(estado__iexact='conforme').count(),
        'observadas': qs_for_cards.filter(estado__iexact='observado').count(),
        'total': qs_for_cards.count(),
    }

    # 10) Preservar filtros en paginación
    preserved = ''
    if f1:
        preserved += f'&f1={f1}'
    if f2:
        preserved += f'&f2={f2}'
    if r1:
        preserved += f'&r1={r1}'
    if r2:
        preserved += f'&r2={r2}'
    if estado_card:
        preserved += f'&estado_card={estado_card}'

    # 11) Contexto
    context = {
        'usuario_nombre': request.session.get('nombre', 'Usuario'),
        'terminal_name': terminal_name,

        'rows': rows,
        'cards': cards,

        'page_obj': page_obj,
        'preserved': preserved,

        # valores para mantener inputs rellenos
        'f1': f1,
        'f2': f2,
        'r1': r1,
        'r2': r2,

        'estado_card': estado_card,
    }

    return render(request, 'admin_terminal_dashboard.html', context)





def panel_admin_sistema(request):
    if not request.session.get('uid'):
        return redirect('login')

    if request.method == 'POST':
        accion = (request.POST.get('accion') or 'create').lower()
        id_usuario = request.POST.get('id_usuario')

        nombre = (request.POST.get('nombre') or '').strip()
        usuario_login = (request.POST.get('usuario_login') or '').strip()
        contrasena = (request.POST.get('contrasena') or '').strip()
        rol = (request.POST.get('rol') or '').strip()
        activo = bool(request.POST.get('activo'))
        terminal_id = request.POST.get('id_terminal') or None
        celular = (request.POST.get('celular') or '').strip()

        if accion == 'delete' and id_usuario:
            usuario = Usuario.objects.filter(pk=id_usuario).first()
            if usuario:
                Tecnico.objects.filter(id_usuario=usuario).delete()
                usuario.delete()
            return redirect('panel_admin_sistema')

        if nombre and usuario_login and rol:

            if accion == 'create' and Usuario.objects.filter(usuario_login=usuario_login).exists():
                return redirect('panel_admin_sistema')

            if accion == 'update' and id_usuario:
                u = Usuario.objects.filter(pk=id_usuario).first()
                if not u:
                    return redirect('panel_admin_sistema')
            else:
                u = Usuario()
                if hasattr(u, 'fecha_ingreso'):
                    u.fecha_ingreso = timezone.now().date()

            u.nombre = nombre
            u.usuario_login = usuario_login

            if contrasena:
                u.contrasena = contrasena

            u.rol = rol

            if hasattr(u, 'activo'):
                u.activo = activo

            u.id_terminal_id = terminal_id if terminal_id else None
            u.save()

            if rol == "tecnico":
                tecnico, creado = Tecnico.objects.get_or_create(
                    id_usuario=u,
                    defaults={
                        "celular": celular,
                        "fecha_creacion": timezone.now()
                    }
                )
                if not creado:
                    tecnico.celular = celular
                    tecnico.save()
            else:
                Tecnico.objects.filter(id_usuario=u).delete()

        return redirect('panel_admin_sistema')

    qs = Usuario.objects.select_related('id_terminal').order_by('id_usuario')

    paginator = Paginator(qs, 12)
    page_num = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_num)
    except:
        page_obj = paginator.page(1)

    usuarios_rows = []

    roles = {
        "admin_sistema": "Administrador del Sistema",
        "coordinador": "Coordinador",
        "tecnico": "Técnico",
        "control_interno": "Control Interno",
        "admin_terminal": "Administrador de Terminal",
    }

    for u in page_obj.object_list:
        tecnico = Tecnico.objects.filter(id_usuario=u).first()

        activo_val = getattr(u, 'activo', True)
        activo_bool = bool(activo_val)

        usuarios_rows.append({
            'id': u.id_usuario,
            'fecha_ingreso': getattr(u, 'fecha_ingreso', None),
            'nombre': u.nombre,
            'usuario_login': u.usuario_login,
            'contrasena': u.contrasena or '',
            'celular': tecnico.celular if tecnico else '',
            'rol': u.rol,
            'rol_mostrar': roles.get(u.rol, u.rol),
            'terminal_id': getattr(u, 'id_terminal_id', '') or '',
            'activo': activo_bool,
            'activo_raw': '1' if activo_bool else '0',
        })

    context = {
        'usuario_nombre': request.session.get('nombre', 'Usuario'),
        'usuarios': usuarios_rows,
        'page_obj': page_obj,
        'terminales': Terminal.objects.all().order_by('nombre_terminal'),
        'hoy': timezone.now().date(),
    }

    return render(request, 'admin_sistema_dashboard.html', context)


#def panel_admin_sistema(request):
 #   maybe_redirect = _require_session(request)
 #   if maybe_redirect: 
 #       return maybe_redirect
 #   return render(request, 'placeholder.html', {'titulo': 'Panel Admin Sistema'})










def exportar_incidencias_excel(request):
    """
    Genera un archivo xlsx con las incidencias según filtros GET.
    """

    # ------- info de sesión (para producción hoy) -------
    uid = request.session.get("uid")
    produccion_hoy = request.GET.get("produccion_hoy")

    # ------- Leer filtros GET (mismos nombres que en el dashboard) -------
    f1 = request.GET.get("f1")    # fecha incidencia desde
    f2 = request.GET.get("f2")    # fecha incidencia hasta
    r1 = request.GET.get("r1")    # fecha revision desde
    r2 = request.GET.get("r2")    # fecha revision hasta
    terminal_filter = request.GET.get("terminal")
    estado_filter = request.GET.get("estado")
    usuario_filter = (request.GET.get("usuario") or "").strip()
    motivo_filter  = (request.GET.get("motivo") or "").strip()
    ci_filter      = (request.GET.get("ci") or "").strip()

    # ------- Query base -------
    qs = (
        Incidencia.objects
        .select_related("id_bc", "id_usuario", "id_bc__id_terminal")
        .order_by("-fecha_revision", "-id_incidencia")
    )

    # ------- Aplicar filtros (igual que en panel_control_interno) -------
    if f1 and f2:
        try:
            d1 = date.fromisoformat(f1)
            d2 = date.fromisoformat(f2)
            if d1 > d2:
                d1, d2 = d2, d1
            qs = qs.filter(fecha_incidencia__range=(d1, d2))
        except ValueError:
            pass

    if r1 and r2:
        try:
            rd1 = date.fromisoformat(r1)
            rd2 = date.fromisoformat(r2)
            if rd1 > rd2:
                rd1, rd2 = rd2, rd1
            qs = qs.filter(fecha_revision__range=(rd1, rd2))
        except ValueError:
            pass

    if terminal_filter:
        qs = qs.filter(id_bc__id_terminal_id=terminal_filter)

    # 🔹 mismo criterio de estado que en el panel
    if estado_filter:
        estado_filter_norm = (estado_filter or "").lower().replace("ó", "o")

        if estado_filter_norm.startswith("observ"):
            qs = qs.filter(estado__icontains="observ")
        elif estado_filter_norm.startswith("pend"):
            qs = qs.filter(estado__icontains="pendiente")
        elif estado_filter_norm.startswith("resu"):
            qs = qs.filter(estado__icontains="resuelto")
        elif estado_filter_norm.startswith("conf"):
            qs = qs.filter(estado__icontains="conforme")

    if usuario_filter:
        qs = qs.filter(
            Q(id_bc__nombre__icontains=usuario_filter) |
            Q(id_bc__usuario__icontains=usuario_filter)
        )

    if motivo_filter:
        qs = qs.filter(motivo__icontains=motivo_filter)

    if ci_filter:
        qs = qs.filter(id_usuario__usuario_login__icontains=ci_filter)
        

    # 🎯 FILTRO: Producción hoy
    if produccion_hoy:
        today = timezone.localdate()

        rol = (request.session.get("rol") or "").lower()

        # Si es CONTROL INTERNO: solo lo suyo
        if rol == "control_interno" and uid:
            qs = qs.filter(id_usuario_id=uid, fecha_revision=today)

        # Si es ADMIN/otros paneles: todo lo de hoy
        else:
            qs = qs.filter(fecha_revision=today)


    # Limitar filas
    MAX_ROWS = 5000
    qs = qs[:MAX_ROWS]

    # ------- Construir workbook -------
    wb = Workbook()
    ws = wb.active
    ws.title = "Incidencias"

    # 👇 NUEVOS HEADERS (sin evidencia, pero con respuesta y fecha respuesta)
    headers = [
        "Fecha de incidencia",
        "Nombre (boletero/cajero)",
        "Usuario",
        "Cargo",
        "Terminal",
        "Control interno",
        "Estado",
        "Motivo",
        "Fecha de revisión",
        "Respuesta administrador",
        "Fecha soluciòn",
    ]
    ws.append(headers)

    # rellenar filas
    for inc in qs:
        bc = getattr(inc, "id_bc", None)
        bc_nombre  = getattr(bc, "nombre", "")  if bc else ""
        bc_usuario = getattr(bc, "usuario", "") if bc else ""
        bc_cargo   = getattr(bc, "cargo", "")   if bc else ""
        term_obj   = getattr(bc, "id_terminal", None)
        terminal_name = getattr(term_obj, "nombre_terminal", "") if term_obj else (
            getattr(bc, "id_terminal", "") if bc else ""
        )

        control_interno = getattr(inc, "id_usuario", None)
        control_interno_name = getattr(control_interno, "nombre", "") if control_interno else ""

        # normalizar estado = igual que en el panel
        estado_val = (getattr(inc, "estado", "") or "").lower().replace("ó", "o")
        if estado_val.startswith("observ"):
            estado_text = "Observado"
        elif estado_val.startswith("pend"):
            estado_text = "Pendiente"
        elif estado_val.startswith("resu"):
            estado_text = "Resuelto"
        else:
            estado_text = "Conforme"

        motivo = getattr(inc, "motivo", "") or ""

        fecha_incid = getattr(inc, "fecha_incidencia", None)
        fecha_rev   = getattr(inc, "fecha_revision", None)

        # 👇 NUEVOS CAMPOS
        solucion_admin = getattr(inc, "solucion_admin", "") or ""
        fecha_resp_obj = getattr(inc, "fecha_solucion", None)  

        row = [
            fecha_incid.isoformat() if fecha_incid else "",
            bc_nombre,
            bc_usuario,
            bc_cargo,
            terminal_name,
            control_interno_name,
            estado_text,
            motivo,
            fecha_rev.isoformat() if fecha_rev else "",
            solucion_admin,
            fecha_resp_obj.isoformat() if fecha_resp_obj else "",
        ]
        ws.append(row)

    # Ajustar anchos (11 columnas ahora)
    column_widths = [18, 30, 15, 12, 14, 22, 12, 40, 18, 40, 22]
    for i, width in enumerate(column_widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = width

    # Guardar workbook en memoria y devolver
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "incidencias_export.xlsx"
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response





@require_POST
def resolver_incidencia(request):
    # Verificar sesión como en el panel
    maybe_redirect = _require_session(request)
    if maybe_redirect:
        return maybe_redirect

    inc_id = request.POST.get('id_incidencia')
    incidencia = get_object_or_404(Incidencia, pk=inc_id)

    # Campos del formulario
    solucion_txt = request.POST.get('solucion_admin', '').strip()
    fecha_sol_str = request.POST.get('fecha_solucion', '')
    evidencia_file = request.FILES.get('evidencia_solucion')

    # Guardar solución
    incidencia.solucion_admin = solucion_txt

    # ⭐ FECHA DE SOLUCIÓN → FECHA LOCAL DE PERÚ (CORRECCIÓN)
    incidencia.fecha_solucion = timezone.localdate()

    # Evidencia de solución (si adjuntan)
    if evidencia_file:
        incidencia.evidencia_solucion = evidencia_file

    # Actualizar estado
    incidencia.estado = 'pendiente'

    incidencia.save()

    messages.success(request, 'La incidencia fue actualizada correctamente.')
    return redirect('panel_admin_terminal')






@require_POST
def actualizar_estado_control_interno(request):
    inc_id = request.POST.get('id_incidencia')
    nuevo_estado = request.POST.get('nuevo_estado')

    incidencia = get_object_or_404(Incidencia, pk=inc_id)

    # Control interno valida los estados finales
    if nuevo_estado == "resuelto":
        incidencia.estado = "resuelto"
    elif nuevo_estado == "observado":
        incidencia.estado = "observado"

    
    incidencia.save()

    messages.success(request, "Estado actualizado correctamente.")
    return redirect("panel_control_interno")




def panel_incidencias(request):
    maybe_redirect = _require_session(request)
    if maybe_redirect:
        return maybe_redirect

    # ==========================
    # 🔍 Filtros GET
    # ==========================
    produccion_hoy = request.GET.get("produccion_hoy")
    # Fecha incidencia
    f1 = request.GET.get("f1")   # desde
    f2 = request.GET.get("f2")   # hasta

    # Fecha revisión
    r1 = request.GET.get("r1")
    r2 = request.GET.get("r2")

    terminal_filter = request.GET.get("terminal")
    estado_filter = request.GET.get("estado")
    usuario_filter = (request.GET.get("usuario") or "").strip()
    motivo_filter = (request.GET.get("motivo") or "").strip()
    ci_filter = (request.GET.get("ci") or "").strip()

    # ==========================
    # Base Query
    # ==========================

    qs = (
        Incidencia.objects
        .select_related("id_bc", "id_usuario", "id_bc__id_terminal")
        .order_by("-fecha_revision", "-id_incidencia")
    )

    # ==========================
    # 🎯 Filtro FECHA INCIDENCIA
    # ==========================
    if f1 and f2:
        try:
            d1 = date.fromisoformat(f1)
            d2 = date.fromisoformat(f2)
            if d1 > d2:
                d1, d2 = d2, d1
            qs = qs.filter(fecha_incidencia__range=(d1, d2))
        except:
            pass

    # ==========================
    # 🎯 Filtro FECHA REVISIÓN
    # ==========================
    if r1 and r2:
        try:
            d1 = date.fromisoformat(r1)
            d2 = date.fromisoformat(r2)
            if d1 > d2:
                d1, d2 = d2, d1
            qs = qs.filter(fecha_revision__range=(d1, d2))
        except:
            pass

    # ==========================
    # 🎯 Filtro Terminal
    # ==========================
    if terminal_filter:
        qs = qs.filter(id_bc__id_terminal_id=terminal_filter)

    # ==========================
    # 🎯 Filtro Estado NORMALIZADO
    # ==========================
    if estado_filter:
        # viene como "Conforme", "Observado", "Pendiente", "Resuelto"
        estado_filter_norm = (estado_filter or "").lower().replace("ó", "o")

        if estado_filter_norm.startswith("observ"):
            qs = qs.filter(estado__icontains="observ")
        elif estado_filter_norm.startswith("pend"):
            qs = qs.filter(estado__icontains="pendiente")
        elif estado_filter_norm.startswith("resu"):
            qs = qs.filter(estado__icontains="resuelto")
        elif estado_filter_norm.startswith("conf"):
            qs = qs.filter(estado__icontains="conforme")


    # ==========================
    # 🎯 Usuario boletero/cajero
    # ==========================
    if usuario_filter:
        qs = qs.filter(
            Q(id_bc__nombre__icontains=usuario_filter) |
            Q(id_bc__usuario__icontains=usuario_filter)
        )

 # 🎯 FILTRO: Producción hoy
    if produccion_hoy:
        today = timezone.localdate()
        qs = qs.filter(fecha_revision=today)

    # ==========================
    # 🎯 Control interno
    # ==========================
    if ci_filter:
        qs = qs.filter(id_usuario__usuario_login__icontains=ci_filter)


    # ==========================
    #  LIMIT TOP 100
    # ==========================
    qs = qs[:100]

    # ==========================
    #  Paginación
    # ==========================
    paginator = Paginator(qs, 20)
    page_num = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_num)
    except:
        page_obj = paginator.page(1)

    # ==========================
    #  Construcción de tabla rows
    # ==========================
    rows = []

    for inc in page_obj.object_list:

        bc = inc.id_bc
        term = bc.id_terminal if bc else None

        # NORMALIZAR ESTADO (4 estados posibles)
        estado_val = (inc.estado or "").lower().replace("ó", "o")

        if estado_val.startswith("observ"):
            estado = "Observado"
        elif estado_val.startswith("pend"):
            estado = "Pendiente"
        elif estado_val.startswith("resu"):
            estado = "Resuelto"
        else:
            estado = "Conforme"


        evidencia = inc.evidencia.url if inc.evidencia else ""

        rows.append({
            "id_incidencia": inc.id_incidencia,  # 👈 NECESARIO PARA EL POST
            "fecha": inc.fecha_incidencia,
            "nombre": bc.nombre if bc else "—",
            "usuario": bc.usuario if bc else "—",
            "cargo": bc.cargo if bc else "—",
            "terminal": term.nombre_terminal if term else "—",
            "control_interno": inc.id_usuario.nombre if inc.id_usuario else "—",
            "estado": estado,
            "motivo": inc.motivo or "—",
            "evidencia": evidencia,
            "fecha_revision": inc.fecha_revision,
            "solucion_admin": inc.solucion_admin or "",  # 👈 para el Ver respuesta
            "evidencia_solucion": (
                inc.evidencia_solucion.url if getattr(inc, "evidencia_solucion", None) else ""
            ),  # 👈 evidencia de solución
        })

    # ==========================
    #  Preservar filtros para paginación
    # ==========================
    preserved = ""
    for k in ("f1", "f2", "r1", "r2", "terminal", "estado", "usuario", "motivo", "ci"):
        v = request.GET.get(k)
        if v:
            preserved += f"&{k}={v}"

    # ==========================
    # Contexto final
    # ==========================
    context = {
        "usuario_nombre": request.session.get("nombre", "Usuario"),
        "terminal_actual": request.session.get("terminal") or "—",

        "rows": rows,
        "page_obj": page_obj,
        "preserved": preserved,

        # reutilizamos valores para mantenerlos en los inputs
        "f1": f1 or "",
        "f2": f2 or "",
        "r1": r1 or "",
        "r2": r2 or "",
        "terminal_selected": terminal_filter or "",
        "estado": estado_filter or "",
        "usuario": usuario_filter or "",
        "motivo": motivo_filter or "",
        "ci": ci_filter or "",

        "boleteros": BoleteroCajero.objects.all(),
        "terminales": Terminal.objects.all().order_by("id_terminal"),

        # NUEVOS SELECTS
        "usuarios_bc": BoleteroCajero.objects.filter(estado="activo").order_by("usuario"),
        "usuarios_ci": Usuario.objects.filter(rol="control_interno").order_by("nombre"),
            
        "boleteros": BoleteroCajero.objects.all(),
        "terminales": Terminal.objects.all().order_by("id_terminal"),
        "control_internos": Usuario.objects.filter(rol="control_interno"),
        
        
    }
    return render(request, 'admin_incidencias_dashboard.html', context)









def panel_boleteros(request):
    # 1) Validar sesión
    if not request.session.get('uid'):
        return redirect('login')

    # 2) Procesar POST (crear / editar / eliminar)
    if request.method == 'POST':
        accion = request.POST.get('accion')

        # -------- CREAR --------
        if accion == 'crear':
            nombre = (request.POST.get('nombre') or '').strip()
            usuario = (request.POST.get('usuario') or '').strip()
            cargo = (request.POST.get('cargo') or '').strip()
            estado = (request.POST.get('estado') or '').strip()
            terminal_id = request.POST.get('id_terminal') or None

            if nombre and usuario and cargo and estado:
                bc = BoleteroCajero(
                    nombre=nombre,
                    usuario=usuario,
                    cargo=cargo,
                    estado=estado,
                    fecha_creacion=timezone.localtime() 
                )
                if terminal_id:
                    bc.id_terminal_id = terminal_id
                bc.save()

            return redirect('panel_boleteros')

        # -------- EDITAR --------
        if accion == 'editar':
            id_bc = request.POST.get('id_bc')
            bc = get_object_or_404(BoleteroCajero, pk=id_bc)

            bc.nombre = (request.POST.get('nombre') or '').strip()
            bc.usuario = (request.POST.get('usuario') or '').strip()
            bc.cargo = (request.POST.get('cargo') or '').strip()
            bc.estado = (request.POST.get('estado') or '').strip()

            terminal_id = request.POST.get('id_terminal') or None
            if terminal_id:
                bc.id_terminal_id = terminal_id
            else:
                bc.id_terminal = None

            bc.save()
            return redirect('panel_boleteros')

        # -------- ELIMINAR --------
        if accion == 'eliminar':
            id_bc = request.POST.get('id_bc')
            bc = get_object_or_404(BoleteroCajero, pk=id_bc)
            bc.delete()
            return redirect('panel_boleteros')

    # 3) GET normal: listar boleteros/cajeros
    qs = (
        BoleteroCajero.objects
        .select_related('id_terminal')
        .order_by('nombre')
    )

    # Búsqueda rápida opcional ?q=
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(usuario__icontains=q) |
            Q(cargo__icontains=q) |
            Q(estado__icontains=q) |
            Q(id_terminal__nombre_terminal__icontains=q)
        )

    # Paginación
    paginator = Paginator(qs, 15)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    try:
        page_obj = paginator.page(page_num)
    except EmptyPage:
        page_obj = paginator.page(1)

    filas = []
    for b in page_obj.object_list:
        term_obj = getattr(b, 'id_terminal', None)
        term_name = getattr(term_obj, 'nombre_terminal', None) if term_obj else None
        if not term_name:
            term_name = term_obj or '—'

        filas.append({
            'id_bc': b.id_bc,
            'nombre': b.nombre,
            'usuario': b.usuario,
            'cargo': b.cargo,
            'estado': b.estado,
            'terminal': term_name,
            'fecha_creacion': b.fecha_creacion,
        })

    context = {
        'usuario_nombre': request.session.get('nombre', 'Usuario'),
        'boleteros_rows': filas,
        'page_obj': page_obj,
        'terminales': Terminal.objects.all().order_by('nombre_terminal'),
        'hoy': timezone.now().date(),
    }
    return render(request, 'admin_boleteros_dashboard.html', context)