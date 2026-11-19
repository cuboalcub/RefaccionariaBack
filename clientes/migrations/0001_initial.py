import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sucursales', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=150)),
                ('apellido_paterno', models.CharField(max_length=150)),
                ('apellido_materno', models.CharField(blank=True, max_length=150, null=True)),
                ('telefono', models.CharField(max_length=15)),
                ('correo', models.EmailField(blank=True, max_length=254, null=True)),
                ('direccion', models.CharField(blank=True, max_length=250, null=True)),
                ('rfc', models.CharField(blank=True, max_length=13, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id_sucursal', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='clientes',
                    to='sucursales.sucursal',
                )),
            ],
        ),
    ]
