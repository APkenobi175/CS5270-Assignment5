# Turn raw JSON data into python objects

import json

import jsonschema


# JSON schema for Widget Requests (HW6 Appendix A)
REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "pattern": "^(create|delete|update)$"},
        "requestId": {"type": "string"},
        "widgetId": {"type": "string"},
        "owner": {"type": "string", "pattern": "^[A-Za-z ]+$"},
        "label": {"type": "string"},
        "description": {"type": "string"},
        "otherAttributes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["name", "value"],
            },
        },
    },
    "required": ["type", "requestId", "widgetId", "owner"],
}


class ParserException(Exception):
    # Custom exception for parsing errors
    pass


class OtherAttribute:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def to_dict(self):
        # convert the other attributes to a dictionary
        return {"name": self.name, "value": self.value}


class WidgetRequest:
    def __init__(self, request_type, request_id, widget_id, owner, label=None, description=None, other_attributes=None):
        self.request_type = request_type
        self.request_id = request_id
        self.widget_id = widget_id
        self.owner = owner
        self.label = label
        self.description = description
        self.other_attributes = other_attributes or []


class WidgetRequestFactory:
    def fromJson(self, text):
        # Parse a JSON string into a WidgetRequest object
        try:
            data = json.loads(text)
        except Exception as e:
            raise ParserException("Invalid JSON: " + str(e))

        return self.fromDict(data)

    def fromDict(self, data):
        # 1. Validate a dict against the schema and build a WidgetRequest from it
        try:
            jsonschema.validate(data, REQUEST_SCHEMA)
        except Exception as e:
            raise ParserException("Invalid widget request: " + str(e))

        # 2. Add the other attributes to the WidgetRequest
        other_attributes = []
        for attr in data.get("otherAttributes", []):
            other_attributes.append(OtherAttribute(attr["name"], attr["value"]))

        # 3. Create the WidgetRequest object
        return WidgetRequest(
            request_type=data["type"],
            request_id=data["requestId"],
            widget_id=data["widgetId"],
            owner=data["owner"],
            label=data.get("label"),
            description=data.get("description"),
            other_attributes=other_attributes,
        )


class Widget:
    def __init__(self, widget_id, owner, label=None, description=None,
                 other_attributes=None):
        self.widget_id = widget_id
        self.owner = owner
        self.label = label
        self.description = description
        self.other_attributes = other_attributes or []

    def to_dict(self):
        # Convert the widget to a plain dict
        other_attributes = []
        for attr in self.other_attributes:
            other_attributes.append(attr.to_dict())

        return {
            "id": self.widget_id,
            "owner": self.owner,
            "label": self.label,
            "description": self.description,
            "otherAttributes": other_attributes,
        }

    def to_json(self):
        # convert the object to a JSON string
        return json.dumps(self.to_dict())


class WidgetFactory:
    def fromRequest(self, request):
        # Build a Widget from the data in a WidgetRequest
        return Widget(
            widget_id=request.widget_id,
            owner=request.owner,
            label=request.label,
            description=request.description,
            other_attributes=list(request.other_attributes),
        )
