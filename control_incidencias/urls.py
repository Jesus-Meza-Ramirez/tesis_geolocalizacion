# control_incidencias/urls.py
from django.contrib import admin
from django.urls import path, include     # <-- include agregado
from django.conf import settings
from webui.views import exportar_incidencias_excel
from django.conf.urls.static import static
from webui.views import (
    login_view, logout_view, dashboard_redirect,
    panel_control_interno, panel_admin_terminal, panel_admin_sistema, actualizar_estado_control_interno
)
from webui import views   


urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth y home
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', dashboard_redirect, name='home'),

    # Paneles principales
    path('panel/control-interno/', panel_control_interno, name='panel_control_interno'),
    path('panel/admin-terminal/', panel_admin_terminal, name='panel_admin_terminal'),
    path('panel/admin-sistema/', panel_admin_sistema, name='panel_admin_sistema'),

    # Apps con include
    path("incidencias/", include("incidencias.urls")),
    path("webui/", include("webui.urls")),  # 👈 FALTABA ESTO


    path('panel/reportes/export-excel/', exportar_incidencias_excel, name='export_excel'),
    
    
    path("ci/estado/", actualizar_estado_control_interno, name="actualizar_estado_control_interno"),
    
    path("panel/incidencias/", views.panel_incidencias, name="panel_incidencias"),
    
    path("panel/boleteros/", views.panel_boleteros, name="panel_boleteros"),
    
    path(
    'panel/tecnicos/<int:id_tecnico>/zona/',
    views.asignar_zona_tecnico,
    name='asignar_zona_tecnico'
    ),
    
    path(
    'panel/tecnicos/<int:id_tecnico>/zona/guardar/',
    views.guardar_zona_tecnico,
    name='guardar_zona_tecnico'
    ),
    
    path(
    'panel/tecnicos/<int:id_tecnico>/zona/ver/',
    views.ver_zona_tecnico,
    name='ver_zona_tecnico'
    ),
    path("buscar-cliente/", views.buscar_cliente, name="buscar_cliente"),
    
    path(
    "panel/tecnico/",
    views.panel_tecnico,
    name="panel_tecnico"
    ),
    
    path(
    "panel/tecnico/atender/",
    views.atender_orden_tecnico,
    name="atender_orden_tecnico"
    ),
    
    path(
    "panel/tecnicos/asignar-zona/",
    views.guardar_asignacion_zona,
    name="guardar_asignacion_zona"
    ),
    
    path("panel/zonas/", views.panel_zonas, name="panel_zonas"),
    
    path(
    "panel/zonas/nueva/",
    views.crear_zona,
    name="crear_zona"
    ),
    
    path(
    "panel/zonas/guardar/",
    views.guardar_zona,
    name="guardar_zona"
    ),
    
    
    path(
    "panel/zonas/<int:id_zona>/ver/",
    views.ver_zona,
    name="ver_zona"
    ),

    path(
        "panel/zonas/<int:id_zona>/editar/",
        views.editar_zona,
        name="editar_zona"
    ),

    path(
        "panel/zonas/<int:id_zona>/actualizar/",
        views.actualizar_zona,
        name="actualizar_zona"
    ),
    
    path(
    "panel/tecnicos/<int:id_tecnico>/zonas/ver/",
    views.ver_zonas_tecnico,
    name="ver_zonas_tecnico"
    ),
    
    path(
    "panel/admin-sistema/ordenes/",
    views.panel_ordenes_admin,
    name="panel_ordenes_admin"
    ),
    
    path(
    "ordenes/<int:id_orden>/eliminar/",
    views.eliminar_orden,
    name="eliminar_orden"
    ),
    
    path("ordenes/<int:id_orden>/datos/", views.obtener_orden_editar, name="obtener_orden_editar"),
    path("ordenes/<int:id_orden>/actualizar/", views.actualizar_orden, name="actualizar_orden"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
