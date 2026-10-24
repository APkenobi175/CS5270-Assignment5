# Turn raw JSON data into python objects

import json

import jsonschema


# JSON schema for widget requests (Appendix A)
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

    def toDict(self):
        # convert the other attributes to a dictionary
        return {"name": self.name, "value": self.value}


class WidgetRequest:
    # Widget request object (The JSON converted to a Python object)
    def __init__(self, requestType, requestId, widgetId, owner, label=None, description=None, otherAttributes=None):
        self.requestType = requestType
        self.requestId = requestId
        self.widgetId = widgetId
        self.owner = owner
        self.label = label
        self.description = description
        self.otherAttributes = otherAttributes or []




class Widget:
    def __init__(self, widgetId, owner, label=None, description=None,
                 otherAttributes=None):
        self.widgetId = widgetId
        self.owner = owner
        self.label = label
        self.description = description
        self.otherAttributes = otherAttributes or []

    def toDict(self):
        # Convert the widget to a plain dict
        otherAttributes = []
        for attr in self.otherAttributes:
            otherAttributes.append(attr.toDict())

        return {
            "id": self.widgetId,
            "owner": self.owner,
            "label": self.label,
            "description": self.description,
            "otherAttributes": otherAttributes,
        }

    def toJson(self):
        # convert the object to a JSON string
        return json.dumps(self.toDict())




#------- Factories for constructing objects -------- (Factory pattern from cs5700)

class WidgetFactory:
    def fromRequest(self, request):
        # Build a Widget from the data in a WidgetRequest
        return Widget(
            widgetId=request.widgetId,
            owner=request.owner,
            label=request.label,
            description=request.description,
            otherAttributes=list(request.otherAttributes),
        )



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
        otherAttributes = []
        for attr in data.get("otherAttributes", []):
            otherAttributes.append(OtherAttribute(attr["name"], attr["value"]))

        # 3. Create the WidgetRequest object
        return WidgetRequest(
            requestType=data["type"],
            requestId=data["requestId"],
            widgetId=data["widgetId"],
            owner=data["owner"],
            label=data.get("label"),
            description=data.get("description"),
            otherAttributes=otherAttributes,
        )
