from typing import Any, List, Optional

class DataField:
    def __init__(self, name: str, field_type: str, description: Optional[str] = None, section: Optional[str] = None):
        self.name = name
        self.field_type = field_type
        self.description = description
        self.section = section

    def to_dict(self) -> dict:
        """Convert DataField to dictionary representation"""
        return {
            "name": self.name,
            "type": self.field_type,
            "description": self.description,
            "section": self.section
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DataField':
        """Create DataField from dictionary"""
        return cls(
            name=data.get("name"),
            field_type=data.get("type"),
            description=data.get("description"),
            section=data.get("section")
        )

    def __str__(self) -> str:
        """String representation of the field"""
        desc = f" - {self.description}" if self.description else ""
        return f"{self.name} ({self.field_type}){desc}"

    def __repr__(self) -> str:
        return f"DataField(name='{self.name}', field_type='{self.field_type}')"


# Factory function to create all bariatric surgery fields matching Data_dictionary.json
def create_bariatric_fields() -> List[DataField]:
    """Create all DataField instances for bariatric surgery data"""
    return [DataField("patient_id", "string", "Unique patient identifier", section="Demographics")]


def generate_data_dictionary() -> List[dict]:
    """Generate the data dictionary in the target JSON format"""
    fields = create_bariatric_fields()
    return [field.to_dict() for field in fields]