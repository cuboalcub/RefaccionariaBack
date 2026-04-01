"""Module defining the movement controller for the application."""

from producto.services.movimiento_service import MovimientoService
from repository.base_controller import BaseDetailController, BaseListController


class MovimientoListCreateView(BaseListController):
    """Controller for listing and creating movements."""

    def __init__(self):
        super().__init__(MovimientoService)


class MovimientoDetailView(BaseDetailController):
    """Controller for retrieving, updating, and deleting a movement by ID."""

    def __init__(self):
        super().__init__(MovimientoService)
