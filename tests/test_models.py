# Unit tests for models.py

import json

import pytest

from models import (
    OtherAttribute,
    ParserException,
    Widget,
    WidgetFactory,
    WidgetRequest,
    WidgetRequestFactory,
)


def makeRequestData():
    # Build a valid create request dict that tests can modify
    return {
        "type": "create",
        "requestId": "req-1",
        "widgetId": "widget-1",
        "owner": "Ammon Phipps",
        "label": "My Label",
        "description": "My Description",
        "otherAttributes": [
            {"name": "color", "value": "red"},
            {"name": "size", "value": "large"},
        ],
    }


#----------------------------
# WidgetRequestFactory Tests
#----------------------------

# From Dict Tests

def testFromDictValidRequestSetsAllFields():
    # Tests that a valid create request sets every field on the WidgetRequest, and makes sure each attribute is set to what is in the test JSON object
    factory = WidgetRequestFactory()

    request = factory.fromDict(makeRequestData())

    assert request.requestType == "create"
    assert request.requestId == "req-1"
    assert request.widgetId == "widget-1"
    assert request.owner == "Ammon Phipps"
    assert request.label == "My Label"
    assert request.description == "My Description"
    assert len(request.otherAttributes) == 2
    assert request.otherAttributes[0].name == "color"
    assert request.otherAttributes[0].value == "red"
    assert request.otherAttributes[1].name == "size"
    assert request.otherAttributes[1].value == "large"


def testFromDictAcceptsUpdateAndDeleteTypes():
    # Tests that update and delete are accepted as request types
    factory = WidgetRequestFactory()

    data = makeRequestData()
    data["type"] = "update"

    data2 = makeRequestData()
    data2["type"] = "delete"

    request = factory.fromDict(data)
    request2 = factory.fromDict(data2)

    assert request.requestType == "update"
    assert request2.requestType == "delete"


def testFromDictOptionalFieldsMissing():
    # Tests that missing optional fields default to None or an empty list
    factory = WidgetRequestFactory()
    data = makeRequestData()
    del data["label"]
    del data["description"]
    del data["otherAttributes"]

    request = factory.fromDict(data)

    assert request.label is None
    assert request.description is None
    assert request.otherAttributes == []


def testFromDictEmptyOtherAttributes():
    # Tests that an empty otherAttributes list is accepted
    factory = WidgetRequestFactory()
    data = makeRequestData()
    data["otherAttributes"] = []

    request = factory.fromDict(data)

    assert request.otherAttributes == []


def testFromDictMissingRequiredFieldsRaise():
    # Tests that a missing required field raises a ParserException
    factory = WidgetRequestFactory()

    fields = ["type", "requestId", "widgetId", "owner"] 

    # Loop through all required fields and make sure each empty one raises an exception
    for i in range(len(fields)):
        data = makeRequestData()
        del data[fields[i]]

        with pytest.raises(ParserException):
            factory.fromDict(data)


def testFromDictInvalidTypeRaises():
    # Tests that a request type other than create/update/delete raises a ParserException
    factory = WidgetRequestFactory()
    data = makeRequestData()
    data["type"] = "explode"

    with pytest.raises(ParserException):
        factory.fromDict(data)



def testFromDictOwnerWithBadCharactersRaises():
    # Tests that an owner with digits, symbols, or no characters raises a ParserException
    factory = WidgetRequestFactory()

    owners = ["Ammon123", "Ammon-Phipps", "Ammon_Phipps", ""]

    for i in range(len(owners)):
        owner = owners[i]
        data = makeRequestData()
        data["owner"] = owner

        with pytest.raises(ParserException):
            factory.fromDict(data)


def testFromDictWrongFieldTypeRaises():
    # Tests that a non-string widgetId raises a ParserException
    factory = WidgetRequestFactory()
    data = makeRequestData()
    data["widgetId"] = 123

    with pytest.raises(ParserException):
        factory.fromDict(data)


def testFromDictNotAnObjectRaises():
    # Tests that input that is not a JSON object raises a ParserException
    factory = WidgetRequestFactory()

    data = [None, [], "create", 5]

    # Tests input for each type in data, loops through all of them
    for i in range(len(data)):
        with pytest.raises(ParserException):
            factory.fromDict(data[i])


#----------------------------
# From JSON Tests
#----------------------------

def testFromJsonValidRequest():
    # Tests that a valid JSON string is parsed into a WidgetRequest
    factory = WidgetRequestFactory()
    text = json.dumps(makeRequestData())

    request = factory.fromJson(text)

    assert request.requestType == "create"
    assert request.widgetId == "widget-1"
    assert request.owner == "Ammon Phipps"
    assert len(request.otherAttributes) == 2


def testFromJsonInvalidJsonRaises():
    # Tests that malformed JSON raises a ParserException
    factory = WidgetRequestFactory()

    with pytest.raises(ParserException):
        factory.fromJson("{ this is not json")


def testFromJsonEmptyStringRaises():
    # Tests that an empty string raises a ParserException
    factory = WidgetRequestFactory()

    with pytest.raises(ParserException):
        factory.fromJson("")


def testFromJsonValidJsonButInvalidRequestRaises():
    # Tests that valid JSON that fails the schema raises a ParserException
    factory = WidgetRequestFactory()

    with pytest.raises(ParserException):
        factory.fromJson('{"type": "create"}')

#----------------------------
# WidgetFactory Tests
#----------------------------

# From Request Tests

def testFromRequestCopiesAllFields():
    # Tests that every field is copied from the WidgetRequest to the Widget
    attributes = [OtherAttribute("color", "red")]
    request = WidgetRequest("create", "req-1", "widget-1", "Ammon Phipps",
                            "My Label", "My Description", attributes)
    factory = WidgetFactory()

    widget = factory.fromRequest(request)

    assert widget.widgetId == "widget-1"
    assert widget.owner == "Ammon Phipps"
    assert widget.label == "My Label"
    assert widget.description == "My Description"
    assert len(widget.otherAttributes) == 1
    assert widget.otherAttributes[0].name == "color"
    assert widget.otherAttributes[0].value == "red"


def testFromRequestDoesNotShareAttributeList():
    # Tests that changing the Widget's attributes does not change the WidgetRequest's adttributes
    request = WidgetRequest("create", "req-1", "widget-1", "Ammon Phipps",
                            otherAttributes=[OtherAttribute("color", "red")])
    factory = WidgetFactory()

    widget = factory.fromRequest(request)
    widget.otherAttributes.append(OtherAttribute("size", "large"))

    assert len(request.otherAttributes) == 1


#----------------------------
# Widget Tests
#----------------------------

def testWidgetToDict():
    # Tests that a Widget with all fields converts to the expected dict
    widget = Widget("widget-1", "Ammon Phipps", "My Label", "My Description",
                    [OtherAttribute("color", "red")])

    result = widget.toDict()

    assert result == {
        "id": "widget-1",
        "owner": "Ammon Phipps",
        "label": "My Label",
        "description": "My Description",
        "otherAttributes": [{"name": "color", "value": "red"}],
    }




def testWidgetToJsonRoundTrips():
    # Tests that toJson produces JSON that parses back to the same data as toDict
    widget = Widget("widget-1", "Ammon Phipps", "My Label", "My Description",
                    [OtherAttribute("color", "red")])

    result = json.loads(widget.toJson())

    assert result == widget.toDict()


#----------------------------
# OtherAttribute Tests
#----------------------------

def testOtherAttributeToDict():
    # Tests that an OtherAttribute converts to a dict correctlu
    attr = OtherAttribute("color", "red")
    assert attr.toDict() == {"name": "color", "value": "red"}
