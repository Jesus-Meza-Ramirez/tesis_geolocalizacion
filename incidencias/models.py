from django.db import models
from django.utils import timezone

class Terminal(models.Model):
    id_terminal = models.CharField(max_length=10, primary_key=True, db_column='id_terminal')
    nombre_terminal = models.CharField(max_length=50, db_column='nombre_terminal')

    def __str__(self):
        return self.nombre_terminal

    class Meta:
        db_table = 'terminales'   # ← nombre real de tu tabla
        managed = False           # ← NO tocar el esquema


class BoleteroCajero(models.Model):
    id_bc = models.AutoField(primary_key=True, db_column='id_bc')
    nombre = models.CharField(max_length=50, db_column='nombre')
    usuario = models.CharField(max_length=20, db_column='usuario', null=True, blank=True)
    cargo = models.CharField(max_length=10, choices=[('boletero','Boletero'),('cajero','Cajero')], db_column='cargo')
    estado = models.CharField(max_length=10, choices=[('activo','Activo'),('inactivo','Inactivo')], db_column='estado')
    # importante: indicar la columna FK real
    id_terminal = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,          # o CASCADE si así está en tu BD
        db_column='id_terminal',
        related_name='boleteros'           # útil para consultas
    )
    fecha_creacion = models.DateTimeField(db_column="fecha_creacion", null=True, blank=True)
    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'boleteros_cajeros'     # ← ojo al nombre exacto de tu tabla
        managed = False


class Incidencia(models.Model):
    ESTADOS = [
        ('conforme', 'Conforme'),
        ('observado', 'Observado'),
        ('pendiente', 'Pendiente'),
        ('resuelto', 'Resuelto'),
    ]
    id_incidencia = models.AutoField(primary_key=True, db_column='id_incidencia')
    id_bc = models.ForeignKey(
        BoleteroCajero,
        on_delete=models.CASCADE,
        db_column='id_bc',
        related_name='incidencias'
    )
    id_usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        db_column='id_usuario',
        related_name='incidencias'
    )
    fecha_incidencia = models.DateField(db_column='fecha_incidencia')
    
    tipo_incidencia = models.CharField(
    max_length=50,
    db_column='tipo_incidencia',
    blank=True,
    
    )

    motivo = models.TextField(blank=True, null=True)
    
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default='observado',      #
        db_column='estado'
    )
    evidencia = models.ImageField(upload_to='evidencias/', blank=True, null=True, db_column='evidencia')
    fecha_revision = models.DateField(db_column='fecha_revision', null=True, blank=True)
    
    
    
    solucion_admin = models.TextField(
        blank=True,
        null=True,
        db_column='solucion_admin'
    )

    evidencia_solucion = models.ImageField(
        upload_to='evidencias_solucion/',
        blank=True,
        null=True,
        db_column='evidencia_solucion'
    )

    fecha_solucion = models.DateField(
        null=True,
        blank=True,
        db_column='fecha_solucion'
    )
    
    
    
    def __str__(self):
        return f"{self.tipo_incidencia} - {self.id_bc.nombre}"

    class Meta:
        db_table = 'incidencias'
        managed = False
        
        
        
        
    
class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    codigo_cliente = models.CharField(max_length=50, unique=True)
    nombre_cliente = models.CharField(max_length=150)
    celular = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255)
    distrito = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)

    latitud = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    observacion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'clientes'


class ZonaTecnico(models.Model):
    id_zona = models.AutoField(primary_key=True)
    nombre_zona = models.CharField(max_length=100)
    id_tecnico = models.ForeignKey('usuarios.Usuario', models.DO_NOTHING, db_column='id_tecnico')
    poligono = models.JSONField()
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'zonas_tecnicos'



        
        

        
class Tecnico(models.Model):
    id_tecnico = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey('usuarios.Usuario', models.DO_NOTHING, db_column='id_usuario')
    celular = models.CharField(max_length=20, blank=True, null=True)
    turno = models.CharField(max_length=50, blank=True, null=True)
    latitud_actual = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitud_actual = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    ultima_actualizacion_ubicacion = models.DateTimeField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tecnicos'
        



class Zona(models.Model):
    id_zona = models.AutoField(primary_key=True)
    nombre_zona = models.CharField(max_length=100)
    id_tecnico = models.ForeignKey(Tecnico, models.DO_NOTHING, db_column='id_tecnico', blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'zonas'


class CoordenadaZona(models.Model):
    id_coordenada = models.AutoField(primary_key=True)
    id_zona = models.ForeignKey(Zona, models.DO_NOTHING, db_column='id_zona')
    latitud = models.DecimalField(max_digits=10, decimal_places=7)
    longitud = models.DecimalField(max_digits=10, decimal_places=7)
    orden_punto = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'coordenadas_zona'
        
        




class OrdenAtencion(models.Model):
    ESTADOS = [
        ('por_atender', 'Por atender'),
        ('atendido', 'Atendido'),
    ]

    id_orden = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column='id_cliente')

    id_tecnico = models.ForeignKey(
        Tecnico,
        models.DO_NOTHING,
        db_column='id_tecnico',
        blank=True,
        null=True
    )

    id_zona = models.ForeignKey(
        Zona,
        models.DO_NOTHING,
        db_column='id_zona',
        blank=True,
        null=True
    )

    fecha_asignacion = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='por_atender')
    indicaciones = models.TextField(blank=True, null=True)
    observacion_tecnico = models.TextField(blank=True, null=True)
    fecha_atencion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordenes_atencion'
        
        
        

class TecnicoZona(models.Model):
    id_tecnico_zona = models.AutoField(primary_key=True)
    id_tecnico = models.ForeignKey(Tecnico, models.DO_NOTHING, db_column='id_tecnico')
    id_zona = models.ForeignKey(Zona, models.DO_NOTHING, db_column='id_zona')
    fecha_asignacion = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tecnico_zona'