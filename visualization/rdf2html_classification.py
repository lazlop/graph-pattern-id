s223_types = {
    "BrickAHU": [
        "brick:AHU", 
        "brick:Air_Handling_Unit"
    ],
    "BrickVAV": [
        "brick:VAV"
    ],
    "BrickPart": [
        "brick:Cooling_Coil",
        "brick:Heating_Coil", 
        "brick:Damper",
        "brick:Supply_Fan",
        "brick:HVAC_Zone",
        "brick:Zone"
    ],
    "BrickPoint": [
        "brick:Outside_Air_Temperature_Sensor",
        "brick:Supply_Air_Temperature_Sensor",
        "brick:Discharge_Air_Temperature_Sensor",
        "brick:Zone_Air_Temperature_Sensor",
        "brick:Mixed_Air_Temperature_Sensor",
        "brick:Return_Air_Temperature_Sensor",
        "brick:Valve_Position_Command",
        "brick:Damper_Position_Command",
        "brick:Frequency_Command",
        "brick:Start_Stop_Command",
        "brick:Position_Command",
        "brick:Filter_Differential_Pressure_Sensor",
        "brick:CO2_Level_Sensor",
        "brick:Occupancy_Sensor",
        "brick:Fan_Status"
    ],
    # Keep existing s223 types for backward compatibility
    "System": ["s223:System"],
    "Equipment": ["s223:Equipment"],
    "Connection": ["s223:Connection"],
    "InletConnectionPoint": [
        "s223:InletConnectionPoint",
        "s223:InletConnectionPoint",
        "p223:ProducerInput",
        "s223:BidirectionalConnectionPoint",
    ],
    "OutletConnectionPoint": [
        "s223:OutletConnectionPoint",
        "s223:FunctionOutput",
        "p223:ProducerOutput",
    ],
    "Function": ["p223:Producer", "s223:Function"],
    "DomainSpace": ["s223:DomainSpace", "s223:PhysicalSpace"],
}

propgraph_labels = {
    "value": ["hasValue"],
    # "range": ["hasMinRange", "hasMaxRange"],
    "direction": ["hasDirection"],
    "aspects": ["hasAspect"],
    "roles": ["hasRole"],
    "medium": ["hasMedium", "ofConstituent", "ofMedium", "hasSignalType", "composedOf"],
    "quantityKind": ["hasQuantityKind"],
    "enumerationKind": ["hasEnumerationKind"],
    "domain": ["hasDomain"],
    "unit": ["qudt/unit", "vocab/unit", "hasUnit"],
}

bacnet_labels = {
    "object-identifier": "http://data.ashrae.org/bacnet/2020#object-identifier",
    "object_type": "http://data.ashrae.org/bacnet/2020#object-type",
    "object-name": "http://data.ashrae.org/bacnet/2020#object-name",
    "description": "http://data.ashrae.org/bacnet/2020#description",
    "address": "http://data.ashrae.org/bacnet/2020#address",
    "device-name": "http://data.ashrae.org/bacnet/2020#device-name",
    "device-identifier": "http://data.ashrae.org/bacnet/2020#device-identifier",
    "vendor-identifier": "http://data.ashrae.org/bacnet/2020#vendor-identifier",
    "vendor-name": "http://data.ashrae.org/bacnet/2020#vendor-name",
    "network-number": "http://data.ashrae.org/bacnet/2020#network-number",
}

skip_edges = [
    "rdfs:label",
    "s223:cnx",
    "s223:connected",
    "rdfs:comment",
    "s223:hasDirection",
    "rdf:type",
    "s223:hasValue",
    "s223:hasAspect",
    "s223:hasMedium",
    "qudt:hasQuantityKind",
    "s223:ofMedium",
    "s223:ofSubstance",
    "s223:hasEnumerationKind",
    "s223:hasDomain",
    # "vocab/unit",
    "qudt:hasUnit",
    "bacnet:object-identifier",
    "bacnet:object-type",
    "bacnet:object-name",
    "bacnet:description",
    "bacnet:address",
    "bacnet:device-name",
    "bacnet:device-identifier",
    "bacnet:vendor-identifier",
    "bacnet:vendor-name",
    "bacnet:network-number",
    "s223:isConnectionPointOf",
    # "s223:hasRef",
    "p223:hasSignalType",
    # "s223:hasMinRange",
    # "s223:hasMaxRange",
    "bob:",
]


def is_wanted_node(predicate):
    for each in skip_edges:
        if each in predicate:
            return False
    return True


class EdgesConfig:
    """
    The contains relationship edge is made wider to emphasize on containment
    Any relatioship not in s223 namespace is dashed (ex. bob)
    """

    def __init__(self, predicate, title):
        self.dashes = False
        self.width = 1
        self.title = title\
        # if "s223" not in predicate:
        #     self.dashes = True
        if "hasPoint" in title:
            self.dashes = True
        if "feeds" in title:
            self.width = 8

    @property
    def args(self):
        return {"title": self.title, "dashes": self.dashes, "width": self.width}
