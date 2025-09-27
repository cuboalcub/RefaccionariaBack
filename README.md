# Refaccionaria backend  


## Pasos para iniciar
### crear venv
```bash
python3 -m venv .venv
```
### Activar en Linux
```bash
source .venv/bin/activate
```
### Activar en Windows PowerShell
```bash
source .venv/bin/activate
```
### Descargar bibliotecas
```bash
pip install -r requierements.txt
```

## Pasos para ejecutar
### pasos para migrar
```bash
python manage.py makemigartions

python manage.py migrate
```
### Corre Django
```bash
python manage.py runserver
```

├── APP/                  # App de usuarios
│   ├── controllers/        # Controladores (views o APIs)
│   │   ├── user_controller.py
│   │
│   ├── services/           # Lógica de negocio
│   │   ├── user_service.py
│   │
│   ├── repositories/       # Acceso a datos (ORM queries)
│   │   ├── user_repository.py
│   │
│   ├── models.py           # Entidades de datos
│   ├── urls.py
│   └── tests.py