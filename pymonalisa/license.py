import base64
from typing import Union


class License:
    """MonaLisa license representation"""
    
    def __init__(self, data: Union[str, bytes]):
        """
        Initialize License
        
        Args:
            data: License data (base64 string or raw bytes)
        """
        if isinstance(data, str):
            try:
                self.data = base64.b64decode(data)
                self.data_b64 = data
            except Exception:
                # If not base64, treat as raw string
                self.data = data.encode('utf-8')
                self.data_b64 = base64.b64encode(self.data).decode('utf-8')
        else:
            self.data = data
            self.data_b64 = base64.b64encode(data).decode('utf-8')
    
    @classmethod
    def from_ticket(cls, ticket_data: Union[str, bytes]) -> 'License':
        """
        Create License from TICKET data
        
        Args:
            ticket_data: ticket data (base64 string)
            
        Returns:
            License: License instance
        """
        return cls(ticket_data)
    
    @property 
    def raw(self) -> bytes:
        """Get raw license data"""
        return self.data
    
    @property
    def b64(self) -> str:
        """Get base64 encoded license data"""
        return self.data_b64
    
    def __str__(self) -> str:
        return self.data_b64
    
    def __repr__(self) -> str:
        return f"License(data='{self.data_b64}')"