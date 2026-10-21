# Generated manually to handle existing row defaults
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sucursales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sucursal',
            name='nombre_sucursal',
            field=models.CharField(default='Sucursal Principal', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sucursal',
            name='codigo_sucursal',
            field=models.CharField(default='SUC001', max_length=50, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sucursal',
            name='codigo_postal',
            field=models.CharField(default='00000', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sucursal',
            name='numero_telefono',
            field=models.CharField(default='0000000000', max_length=15),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sucursal',
            name='correo_electronico',
            field=models.EmailField(default='sucursal@example.com', max_length=254),
            preserve_default=False,
        ),
    ]
