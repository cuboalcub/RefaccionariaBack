from abc import abstractmethod
import abc          
from django.db import models  
from django.forms.models import model_to_dict
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar('T', bound=models.Model)


class IService(Generic[T],abc.ABC):

    @abstractmethod
    def create(self, data) -> Dict[str, Any]:
        pass
        
    
    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, id) -> Dict[str, Any]:
        pass



    @abstractmethod
    def delete(self, id) -> Dict[str, str]:
        pass

    @abstractmethod
    def update(self, id, data) -> Dict[str, Any]:
        pass
    