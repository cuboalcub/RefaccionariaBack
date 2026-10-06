"""Cobertura: repository base, interfaces, usuario, clientes, models __str__."""
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from repository.base_service import BaseService
from repository.base_repository import BaseRepository
from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from clientes.models import Cliente
from clientes.repositories.cliente_repository import ClienteRepository
from clientes.services.cliente_service import ClienteService
from sucursales.models import Sucursal
from inventario.models import Inventario, MovimientoInventario, DetalleInventario, PrecioSucursal
from producto.models import Tipo, Proveedor, Producto
from ventas.models import metodoPago, venta, detalleVenta, Reporte
from usuario.models import Perfil
from usuario.serializers import UserSerializer
from usuario.services.perfil_service import PerfilService
from usuario.services.usuario_services import UserService

pytestmark = pytest.mark.django_db


# ---------- helpers ----------
def sucursal_service(repo=None):
    from sucursales.models import Sucursal as S
    from repository.base_repository import BaseRepository as BR
    return BaseService(model=S, repository=repo or BR(S))


def make_sucursal(ubi="Ubi"):
    return Sucursal.objects.create(ubicacion=ubi)


def make_cliente(suc, **kw):
    base = {"nombre": "Juan", "apellido_paterno": "Perez", "telefono": "5550001111"}
    base.update(kw)
    return Cliente.objects.create(id_sucursal=suc, **base)


# ================= BaseService init / required / _to_dict =================
class TestBaseServiceInit:
    def test_init_none_raises(self):
        with pytest.raises(ValueError):
            BaseService(model=None, repository=None)

    def test_init_no_subclass_raises(self):
        with pytest.raises(ValueError):
            BaseService(model=dict, repository=None)

    def test_required_fields_sucursal(self):
        svc = sucursal_service()
        assert "ubicacion" in svc.required_fields
        assert "id" not in svc.required_fields

    def test_validate_missing_raises(self):
        svc = sucursal_service()
        with pytest.raises(ValueError, match="Faltan campos obligatorios"):
            svc._validate_required_fields({})

    def test_validate_none_value_raises(self):
        svc = sucursal_service()
        with pytest.raises(ValueError, match="Faltan campos obligatorios"):
            svc._validate_required_fields({"ubicacion": None})

    def test_to_dict_none(self):
        assert sucursal_service()._to_dict(None) == {}

    def test_to_dict_fk_raw_id(self):
        suc = make_sucursal()
        c = make_cliente(suc)
        d = ClienteService()._to_dict(c)
        assert d["id_sucursal"] == suc.id

    def test_to_dict_decimal_y_datetime(self):
        p = Producto.objects.create(
            clave="CLV-TO-DICT", nombre="Prod", codigo_barras="123",
            precio_venta=Decimal("10.50"), marca="M", costo=Decimal("5.25"),
        )
        svc = BaseService(model=Producto, repository=BaseRepository(Producto))
        d = svc._to_dict(p)
        assert d["precio_venta"] == "10.50"
        assert d["costo"] == "5.25"
        # datetime isoformat
        suc = make_sucursal("U2")
        c = make_cliente(suc)
        d2 = BaseService(model=Cliente, repository=BaseRepository(Cliente))._to_dict(c)
        assert isinstance(d2["created_at"], str)  # isoformat
        assert "T" in d2["created_at"] or "-" in d2["created_at"]


# ================= BaseService create =================
class TestBaseServiceCreate:
    def test_create_ok(self):
        svc = sucursal_service()
        out = svc.create({"ubicacion": "Centro"})
        assert out["ubicacion"] == "Centro"
        assert Sucursal.objects.filter(ubicacion="Centro").exists()

    def test_create_validacion_faltante(self):
        svc = sucursal_service()
        with pytest.raises(ValueError, match="Error al crear"):
            svc.create({})

    def test_create_validation_error(self):
        repo = Mock()
        repo.create.side_effect = ValidationError("mal")
        svc = BaseService(model=Sucursal, repository=repo)
        # Sucursal required: ubicacion; pasamos ubicacion para llegar al repo
        with pytest.raises(ValueError, match="Error de validación"):
            svc.create({"ubicacion": "X"})

    def test_create_excepcion_generica(self):
        repo = Mock()
        repo.create.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al crear"):
            svc.create({"ubicacion": "X"})


# ================= BaseService get_all =================
class TestBaseServiceGetAll:
    def test_get_all_ok(self):
        make_sucursal("A")
        make_sucursal("B")
        out = sucursal_service().get_all()
        assert len(out) == 2

    def test_get_all_error(self):
        repo = Mock()
        repo.get_all.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al obtener todos"):
            svc.get_all()


# ================= BaseService get_by_id =================
class TestBaseServiceGetById:
    def test_ok(self):
        suc = make_sucursal()
        out = sucursal_service().get_by_id(suc.id)
        assert out["ubicacion"] == suc.ubicacion

    def test_notfound_none(self):
        with pytest.raises(NotFoundError):
            sucursal_service().get_by_id(99999)

    def test_object_does_not_exist(self):
        repo = Mock()
        repo.get_by_id.side_effect = ObjectDoesNotExist("nf")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(NotFoundError):
            svc.get_by_id(1)

    def test_error_generico(self):
        repo = Mock()
        repo.get_by_id.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al obtener por id"):
            svc.get_by_id(1)


# ================= BaseService update =================
class TestBaseServiceUpdate:
    def test_ok(self):
        suc = make_sucursal("Old")
        out = sucursal_service().update(suc.id, {"ubicacion": "New"})
        assert out["ubicacion"] == "New"

    def test_notfound(self):
        with pytest.raises(NotFoundError):
            sucursal_service().update(99999, {"ubicacion": "X"})

    def test_object_does_not_exist(self):
        repo = Mock()
        repo.get_by_id.side_effect = ObjectDoesNotExist("nf")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(NotFoundError):
            svc.update(1, {"ubicacion": "X"})

    def test_validacion(self):
        suc = make_sucursal("V")
        repo = Mock()
        repo.get_by_id.return_value = suc
        repo.update.side_effect = ValidationError("mal")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error de validación"):
            svc.update(suc.id, {"ubicacion": "X"})

    def test_error_generico(self):
        suc = make_sucursal("E")
        repo = Mock()
        repo.get_by_id.return_value = suc
        repo.update.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al actualizar"):
            svc.update(suc.id, {"ubicacion": "X"})


# ================= BaseService delete =================
class TestBaseServiceDelete:
    def test_ok(self):
        suc = make_sucursal()
        out = sucursal_service().delete(suc.id)
        assert "eliminado" in out["message"].lower()
        assert Sucursal.objects.count() == 0

    def test_ok_con_user(self, user):
        suc = make_sucursal()
        out = sucursal_service().delete(suc.id, user=user)
        assert "eliminado" in out["message"].lower()

    def test_notfound(self):
        with pytest.raises(NotFoundError):
            sucursal_service().delete(99999)

    def test_object_does_not_exist_repo(self):
        repo = Mock()
        repo.get_by_id.side_effect = ObjectDoesNotExist("nf")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(NotFoundError):
            svc.delete(1)

    def test_sin_repository_ok(self):
        suc = make_sucursal()
        svc = BaseService(model=Sucursal, repository=None)
        out = svc.delete(suc.id)
        assert "eliminado" in out["message"].lower()

    def test_sin_repository_notfound(self):
        svc = BaseService(model=Sucursal, repository=None)
        with pytest.raises(NotFoundError):
            svc.delete(99999)

    def test_error_generico(self):
        suc = make_sucursal()
        with patch.object(Sucursal, "delete", side_effect=RuntimeError("boom")):
            # instance.delete falla -> ValueError; repo get_by_id devuelve instancia real
            svc = sucursal_service()
            # parchar a nivel instancia es mas simple:
            inst = Sucursal.objects.get(id=suc.id)
            with patch.object(type(inst), "delete", side_effect=RuntimeError("boom")):
                with pytest.raises(ValueError, match="Error al eliminar"):
                    svc.delete(suc.id)


# ================= BaseService filters/exists/count =================
class TestBaseServiceMisc:
    def test_get_by_filters_ok_repo(self):
        suc = make_sucursal("F1")
        make_sucursal("F2")
        repo = Mock()
        repo.get_by_filters.return_value = [suc]
        out = BaseService(model=Sucursal, repository=repo).get_by_filters({"ubicacion": "F1"})
        assert len(out) == 1 and out[0]["ubicacion"] == "F1"

    def test_get_by_filters_sin_repo(self):
        make_sucursal("G1")
        svc = BaseService(model=Sucursal, repository=None)
        out = svc.get_by_filters({"ubicacion": "G1"})
        assert len(out) == 1

    def test_get_by_filters_error(self):
        repo = Mock()
        repo.get_by_filters.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al filtrar"):
            svc.get_by_filters({"ubicacion": "x"})

    def test_exists_ok(self):
        repo = Mock()
        repo.exists.side_effect = [True, False]
        svc = BaseService(model=Sucursal, repository=repo)
        assert svc.exists(1) is True
        assert svc.exists(99999) is False

    def test_exists_real_repo_sin_metodo(self):
        # GAP real: BaseRepository no implementa exists/get_by_filters/count;
        # BaseService lo intenta y deriva en ValueError. Se documenta aqui.
        suc = make_sucursal()
        with pytest.raises(ValueError, match="Error al verificar existencia"):
            sucursal_service().exists(suc.id)

    def test_exists_sin_repo(self):
        suc = make_sucursal()
        svc = BaseService(model=Sucursal, repository=None)
        assert svc.exists(suc.id) is True

    def test_exists_error(self):
        repo = Mock()
        repo.exists.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al verificar existencia"):
            svc.exists(1)

    def test_count_con_repo(self):
        repo = Mock()
        repo.count.side_effect = [1, 1, 0]
        svc = BaseService(model=Sucursal, repository=repo)
        assert svc.count() == 1
        assert svc.count({"ubicacion": "C1"}) == 1
        assert svc.count({"ubicacion": "NADA"}) == 0

    def test_count_real_repo_sin_metodo(self):
        make_sucursal("C1")
        with pytest.raises(ValueError, match="Error al contar"):
            sucursal_service().count()

    def test_count_sin_repo(self):
        make_sucursal("H1")
        make_sucursal("H2")
        svc = BaseService(model=Sucursal, repository=None)
        assert svc.count() == 2
        assert svc.count({"ubicacion": "H1"}) == 1

    def test_count_error(self):
        repo = Mock()
        repo.count.side_effect = RuntimeError("boom")
        svc = BaseService(model=Sucursal, repository=repo)
        with pytest.raises(ValueError, match="Error al contar"):
            svc.count()


# ================= BaseRepository (linea 39 filter) =================
class TestBaseRepository:
    def test_filter_linea39(self):
        make_sucursal("FA")
        make_sucursal("FB")
        repo = BaseRepository(Sucursal)
        out = repo.filter({"ubicacion": "FA"})
        assert len(out) == 1 and out[0].ubicacion == "FA"

    def test_crud_basico(self):
        repo = BaseRepository(Sucursal)
        obj = repo.create({"ubicacion": "R1"})
        assert repo.get_by_id(obj.id).ubicacion == "R1"
        assert repo.get_by_id(99999) is None
        assert len(repo.get_all()) == 1
        repo.update(obj, {"ubicacion": "R2"})
        assert Sucursal.objects.get(id=obj.id).ubicacion == "R2"
        assert repo.delete(obj) is True

    def test_delete_false(self):
        repo = BaseRepository(Sucursal)
        fake = Sucursal(id=99999, ubicacion="x")
        assert repo.delete(fake) is False


# ================= BaseController ramas =================
def _req(data=None):
    m = Mock()
    m.data = data or {}
    return m


class _SvcOK:
    def __init__(self, *a, **k):
        pass

    def get_all(self):
        return [{"id": 1}]

    def create(self, data):
        return {"id": 1, **data}

    def get_by_id(self, pk):
        return {"id": pk}

    def update(self, pk, data):
        return {"id": pk, **data}

    def delete(self, pk):
        return {"message": "ok"}


class TestBaseController:
    def test_list_get(self):
        c = BaseListController.__new__(BaseListController)
        c.service = _SvcOK()
        resp = BaseListController.get(c, _req())
        assert resp.status_code == 200

    def test_list_post_ok(self):
        c = BaseListController.__new__(BaseListController)
        c.service = _SvcOK()
        resp = BaseListController.post(c, _req({"ubicacion": "X"}))
        assert resp.status_code == 201

    def test_list_post_400(self):  # ramas 25-26
        c = BaseListController.__new__(BaseListController)
        bad = Mock()
        bad.create.side_effect = ValueError("mal")
        c.service = bad
        resp = BaseListController.post(c, _req({}))
        assert resp.status_code == 400

    def test_detail_get_ok(self):
        c = BaseDetailController.__new__(BaseDetailController)
        c.service = _SvcOK()
        assert BaseDetailController.get(c, _req(), 1).status_code == 200

    def test_detail_get_404(self):  # rama 39-40
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.get_by_id.side_effect = NotFoundError("nf")
        c.service = bad
        assert BaseDetailController.get(c, _req(), 1).status_code == 404

    def test_detail_get_400(self):  # rama 41-42
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.get_by_id.side_effect = ValueError("mal")
        c.service = bad
        assert BaseDetailController.get(c, _req(), 1).status_code == 400

    def test_detail_put_ok(self):
        c = BaseDetailController.__new__(BaseDetailController)
        c.service = _SvcOK()
        assert BaseDetailController.put(c, _req({"a": 1}), 1).status_code == 200

    def test_detail_put_404(self):  # rama 48-49
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.update.side_effect = NotFoundError("nf")
        c.service = bad
        assert BaseDetailController.put(c, _req({}), 1).status_code == 404

    def test_detail_put_400(self):  # rama 50-51
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.update.side_effect = ValueError("mal")
        c.service = bad
        assert BaseDetailController.put(c, _req({}), 1).status_code == 400

    def test_detail_delete_ok(self):
        c = BaseDetailController.__new__(BaseDetailController)
        c.service = _SvcOK()
        assert BaseDetailController.delete(c, _req(), 1).status_code == 200

    def test_detail_delete_404(self):  # rama 57-58
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.delete.side_effect = NotFoundError("nf")
        c.service = bad
        assert BaseDetailController.delete(c, _req(), 1).status_code == 404

    def test_detail_delete_400(self):  # rama 59-60
        c = BaseDetailController.__new__(BaseDetailController)
        bad = Mock()
        bad.delete.side_effect = ValueError("mal")
        c.service = bad
        assert BaseDetailController.delete(c, _req(), 1).status_code == 400


# ================= interfaces (sin codigo ejecutable salvo ABC) =================
class TestInterfaces:
    def test_abstract_no_instanciables(self):
        from interfaces.service import IService
        from interfaces.repository import IRepository
        from interfaces.controller import ListCreateControllerInterface, DetailControllerInterface
        for cls in (IService, IRepository, ListCreateControllerInterface, DetailControllerInterface):
            with pytest.raises(TypeError):
                cls()  # type: ignore

    def test_metodos_abstractos_definidos(self):
        from interfaces.service import IService
        from interfaces.repository import IRepository
        assert {"create", "get_all", "get_by_id", "delete", "update"} <= set(IService.__abstractmethods__)
        assert {"get_by_id", "get_all", "create", "update", "delete", "filter"} <= set(IRepository.__abstractmethods__)

    def test_subclase_concreta_funciona(self):
        from interfaces.repository import IRepository

        class Mini(IRepository):
            def get_by_id(self, entity_id):
                return None

            def get_all(self):
                return []

            def create(self, data):
                return data

            def update(self, entity, data):
                return entity

            def delete(self, entity):
                return True

            def filter(self, data):
                return []

        assert Mini().get_all() == []
        assert Mini().get_by_id(1) is None
        assert Mini().create({"a": 1}) == {"a": 1}
        assert Mini().update({"id": 1}, {}) == {"id": 1}
        assert Mini().delete({"id": 1}) is True
        assert Mini().filter({"a": 1}) == []


# ================= usuario/serializers =================
class TestUserSerializer:
    def test_fields(self, user):
        s = UserSerializer(user)
        assert set(s.data.keys()) == {"id", "username", "email", "is_active"}
        assert s.data["username"] == "tester"

    def test_serialize_staff(self, staff_user):
        s = UserSerializer(staff_user)
        assert s.data["username"] == "staff"

    def test_deserialize_ok(self, db):
        s = UserSerializer(data={"username": "nuevo", "email": "n@n.com"})
        assert s.is_valid(), s.errors


# ================= perfil_service (12-13,28,38) =================
class TestPerfilService:
    def test_get_by_usuario(self, user, perfil):
        svc = PerfilService()
        out = svc.get_by_usuario(user.id)
        assert out["id_usuario"] == user.id
        assert out["id_sucursal"] == perfil.id_sucursal_id

    def test_get_by_usuario_none(self, user):
        assert PerfilService().get_by_usuario(user.id) is None  # linea 38

    def test_get_or_create_existente(self, user, perfil):
        out = PerfilService().get_or_create(user)
        assert out["id"] == perfil.id

    def test_get_or_create_nuevo(self, user):
        out = PerfilService().get_or_create(user)
        assert out["id_usuario"] == user.id

    def test_update_by_usuario_nuevo(self, user, sucursal):
        out = PerfilService().update_by_usuario(user, {"id_sucursal": sucursal.id})
        assert out["id_sucursal"] == sucursal.id

    def test_update_by_usuario_none_sucursal(self, user, perfil):  # linea 28
        out = PerfilService().update_by_usuario(user, {"id_sucursal": None})
        assert out["id_sucursal"] is None

    def test_update_by_usuario_sucursal_inexistente(self, user, perfil):
        with pytest.raises(ValueError, match="sucursal"):
            PerfilService().update_by_usuario(user, {"id_sucursal": 99999})

    def test_update_sin_sucursal_key(self, user, perfil):
        out = PerfilService().update_by_usuario(user, {})
        assert out["id"] == perfil.id

    def test_to_dict_none(self):
        assert PerfilService()._to_dict(None) is None


# ================= usuario_services (53-54,59,68,73-77,81) =================
class TestUserService:
    def test_get_all_users(self, user):
        assert len(UserService().get_all_users()) == 1

    def test_get_user_by_id(self, user):
        out = UserService().get_user_by_id(user.id)
        assert out["username"] == "tester"

    def test_get_user_by_id_none(self):  # 53-54 + 81
        assert UserService().get_user_by_id(99999) is None

    def test_update_user_none(self):  # 59
        assert UserService().update_user(99999, {"username": "x"}) is None

    def test_update_user_ok_setattr(self, user):  # 68
        out = UserService().update_user(user.id, {"first_name": "Nom", "username": "tester2", "hack": "no"})
        assert out["username"] == "tester2"
        user.refresh_from_db()
        assert user.first_name == "Nom"

    def test_update_user_password(self, user):
        UserService().update_user(user.id, {"password": "nueva123"})
        user.refresh_from_db()
        assert user.check_password("nueva123")

    def test_delete_user_none(self):  # 73-75
        assert UserService().delete_user(99999) is False

    def test_delete_user_ok(self, user):  # 76-77
        assert UserService().delete_user(user.id) is True

    def test_to_dict_none(self):  # 81
        assert UserService()._to_dict(None) is None

    def test_login_ok_y_fail(self, user):
        out = UserService().login("tester", "testpass123")
        assert "access" in out and out["user"]["username"] == "tester"
        assert UserService().login("tester", "mala") is None
        assert UserService().login("nadie", "x") is None

    def test_login_staff(self, staff_user):
        out = UserService().login("staff", "testpass123")
        assert out["user"]["isstaff"] is True

    def test_create_user_faltantes(self):
        with pytest.raises(ValueError, match="Faltan campos"):
            UserService().create_user({"username": "solo"})

    def test_create_user_duplicado(self, user):
        with pytest.raises(ValueError, match="ya existe"):
            UserService().create_user({"username": "tester", "password": "x"})

    def test_create_user_sucursal_mala_borra(self, sucursal):
        n0 = User.objects.count()
        with pytest.raises(ValueError, match="sucursal"):
            UserService().create_user({"username": "tmp1", "password": "x", "id_sucursal": 99999})
        assert User.objects.count() == n0

    def test_create_user_con_sucursal(self, sucursal):
        out = UserService().create_user({"username": "consuc", "password": "x", "id_sucursal": sucursal.id})
        assert out["username"] == "consuc"
        assert Perfil.objects.filter(usuario__username="consuc").exists()

    def test_create_user_sin_sucursal(self):
        out = UserService().create_user({"username": "sinsuc", "password": "x"})
        assert out["username"] == "sinsuc"


# ================= usuario models __str__ + perfil_controller =================
class TestUsuarioModeloYPerfilController:
    def test_perfil_str(self, perfil):
        assert str(perfil) == perfil.usuario.username

    def test_perfil_get(self, auth_client, user, perfil):
        r = auth_client.get("/api/perfil/")
        assert r.status_code == 200
        assert r.data["id_usuario"] == user.id

    def test_perfil_get_jwt(self, jwt_client, user):
        r = jwt_client.get("/api/perfil/")
        assert r.status_code == 200

    def test_perfil_put_ok(self, auth_client, sucursal):
        r = auth_client.put("/api/perfil/", {"id_sucursal": sucursal.id}, format="json")
        assert r.status_code == 200
        assert r.data["id_sucursal"] == sucursal.id

    def test_perfil_put_none(self, auth_client):
        r = auth_client.put("/api/perfil/", {"id_sucursal": None}, format="json")
        assert r.status_code == 200

    def test_perfil_put_400(self, auth_client):
        r = auth_client.put("/api/perfil/", {"id_sucursal": 99999}, format="json")
        assert r.status_code == 400

    def test_perfil_401(self, api_client):
        assert api_client.get("/api/perfil/").status_code == 401


# ================= clientes service/repository =================
class TestClienteService:
    def test_validar_falta(self):
        with pytest.raises(ValueError, match="id_sucursal"):
            ClienteService().create({"nombre": "A", "apellido_paterno": "B", "telefono": "1"})

    def test_validar_none(self, sucursal):
        with pytest.raises(ValueError, match="id_sucursal"):
            ClienteService().create({"nombre": "A", "apellido_paterno": "B", "telefono": "1", "id_sucursal": None})

    def test_validar_sucursal_no_existe(self):
        with pytest.raises(ValueError, match="sucursal"):
            ClienteService().create({"nombre": "A", "apellido_paterno": "B", "telefono": "1", "id_sucursal": 99999})

    def test_create_ok(self, sucursal):
        out = ClienteService().create({"nombre": "A", "apellido_paterno": "B", "telefono": "1", "id_sucursal": sucursal.id})
        assert out["id_sucursal"] == sucursal.id

    def test_update_sucursal_mala(self, sucursal):
        c = make_cliente(sucursal)
        with pytest.raises(ValueError, match="sucursal"):
            ClienteService().update(c.id, {"id_sucursal": 99999})

    def test_update_sucursal_ok(self, sucursal, sucursal_b):
        c = make_cliente(sucursal)
        out = ClienteService().update(c.id, {"id_sucursal": sucursal_b.id, "nombre": "Z"})
        assert out["id_sucursal"] == sucursal_b.id

    def test_update_sin_sucursal(self, sucursal):
        c = make_cliente(sucursal)
        out = ClienteService().update(c.id, {"nombre": "Otro"})
        assert out["nombre"] == "Otro"

    def test_to_dict_none(self):
        assert ClienteService()._to_dict(None) is None

    def test_repository_crud(self, sucursal):
        repo = ClienteRepository()
        obj = repo.create({"id_sucursal": sucursal, "nombre": "R", "apellido_paterno": "P", "telefono": "1"})
        assert repo.get_by_id(obj.id).nombre == "R"
        assert len(repo.filter({"nombre": "R"})) == 1  # cubre filter linea 39
        repo.update(obj, {"nombre": "R2"})
        assert Cliente.objects.get(id=obj.id).nombre == "R2"


# ================= clientes controllers CRUD + 401 + validaciones =================
class TestClienteAPI:
    def _payload(self, suc):
        return {"nombre": "Juan", "apellido_paterno": "Perez", "telefono": "5551234567", "id_sucursal": suc.id}

    def test_401(self, api_client, sucursal):
        assert api_client.get("/api/clientes/").status_code == 401
        assert api_client.post("/api/clientes/", self._payload(sucursal)).status_code == 401
        assert api_client.get("/api/clientes/1/").status_code == 401
        assert api_client.put("/api/clientes/1/", {}).status_code == 401
        assert api_client.delete("/api/clientes/1/").status_code == 401

    def test_crud(self, auth_client, sucursal):
        r = auth_client.post("/api/clientes/", self._payload(sucursal), format="json")
        assert r.status_code == 201
        cid = r.data["id"]
        assert auth_client.get("/api/clientes/").status_code == 200
        assert auth_client.get(f"/api/clientes/{cid}/").status_code == 200
        assert auth_client.put(f"/api/clientes/{cid}/", {"nombre": "Nuevo", "id_sucursal": sucursal.id}, format="json").status_code == 200
        assert auth_client.delete(f"/api/clientes/{cid}/").status_code == 200

    def test_crud_staff_y_jwt(self, staff_user, jwt_client, sucursal):
        # usa staff_user (linea 20 conftest) y jwt_client (linea 61)
        assert staff_user.is_staff is True
        r = jwt_client.post("/api/clientes/", self._payload(sucursal), format="json")
        assert r.status_code == 201

    def test_validaciones(self, auth_client, sucursal):
        bad = {"nombre": "A", "apellido_paterno": "B", "telefono": "1"}
        assert auth_client.post("/api/clientes/", bad, format="json").status_code == 400
        bad2 = dict(bad, id_sucursal=99999)
        assert auth_client.post("/api/clientes/", bad2, format="json").status_code == 400
        c = make_cliente(sucursal)
        assert auth_client.put(f"/api/clientes/{c.id}/", {"id_sucursal": 99999}, format="json").status_code == 400
        assert auth_client.get("/api/clientes/99999/").status_code == 404


# ================= models __str__ restantes =================
class TestModelsStr:
    def test_cliente_str(self, sucursal):
        assert str(make_cliente(sucursal)) == "Juan Perez"

    def test_sucursal_str(self, sucursal):
        assert str(sucursal) == sucursal.ubicacion

    def test_inventario_str(self, inventario):
        assert "Inventario principal" in str(inventario)

    def test_movimiento_str(self):
        m = MovimientoInventario.objects.create(tipo="ENTRADA", cantidad=5, razon="compra")
        assert str(m) == "ENTRADA - 5"

    def test_detalle_inventario_str(self, inventario):
        p = Producto.objects.create(clave="K1", nombre="Prod1", codigo_barras="b1", precio_venta=Decimal("9.99"), marca="M", costo=Decimal("4.00"))
        m = MovimientoInventario.objects.create(tipo="ENTRADA", cantidad=2, razon="r")
        d = DetalleInventario.objects.create(id_producto=p, id_inventario=inventario, id_movimiento=m, cantidad=2)
        assert str(d) == f"{p} - 2"

    def test_precio_sucursal_str(self, sucursal):
        p = Producto.objects.create(clave="K2", nombre="Prod2", codigo_barras="b2", precio_venta=Decimal("9.99"), marca="M", costo=Decimal("4.00"))
        ps = PrecioSucursal.objects.create(id_producto=p, id_sucursal=sucursal, precio_venta=Decimal("12.50"))
        assert "12.50" in str(ps)

    def test_tipo_proveedor_producto_str(self):
        t = Tipo.objects.create(nombre="Refaccion")
        prov = Proveedor.objects.create(nombre="Prov", telefono="123", correo="p@p.com", direccion="dir")
        p = Producto.objects.create(clave="K3", nombre="Bujia", codigo_barras="b3", precio_venta=Decimal("9.99"), marca="M", costo=Decimal("4.00"))
        assert str(t) == "Refaccion" and str(prov) == "Prov" and str(p) == "Bujia"

    def test_reporte_str(self):
        import django.utils.timezone as tz
        ahora = tz.now()
        r = Reporte.objects.create(tipo="day", fecha_inicio=ahora, fecha_fin=ahora, archivo="reportes/x.pdf")
        assert "Reporte day" in str(r)

    def test_ventas_sin_str_no_rompen(self, user, inventario):
        mp = metodoPago.objects.create(tipo="efectivo", descripcion="cash")
        prod = Producto.objects.create(clave="KV", nombre="PV", codigo_barras="bv", precio_venta=Decimal("10"), marca="M", costo=Decimal("5"))
        v = venta.objects.create(id_usuario=user, id_metodoPago=mp, id_inventario=inventario, total=Decimal("100"))
        dv = detalleVenta.objects.create(id_producto=prod, id_venta=v, subtotal=Decimal("100"), cantidad=1)
        assert isinstance(str(mp), str) and isinstance(str(v), str) and isinstance(str(dv), str)
