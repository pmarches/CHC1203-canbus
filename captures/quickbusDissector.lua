local f_can_id = Field.new("can.id")
local f_can_len = Field.new("can.len")


local MEASURMENT_UNIT={
    [0x01]="Meter?",
    [0x02]="Feet",
}

local quickbus_proto = Proto("quickbus","Quick canbus protocol")
quickbus_proto.fields.messagekind=ProtoField.uint16("quickbus.messagekind", "Canbus ID", base.HEX, nil)

quickbus_proto.fields.talker=ProtoField.uint16("quickbus.talker", "Talker Id", base.HEX, nil)
quickbus_proto.fields.measurementunit=ProtoField.uint16("quickbus.measurementunit", "Chain measurement unit", base.DEC, MEASURMENT_UNIT)
quickbus_proto.fields.chainout=ProtoField.uint32("quickbus.chainoutfeet", "Chain out", base.DEC, nil)
quickbus_proto.fields.unknown=ProtoField.bytes("quickbus.unknown", "Unknown bytes", base.NONE)

--quick-canbus-1702295930.pcap

function quickbus_proto.dissector(buffer,pinfo,tree)
    local canIdBuf=f_can_id().tvb
    
    pinfo.cols.info:set("")
    pinfo.cols.protocol = quickbus_proto.name
    local toptree = tree:add(quickbus_proto, buffer(0),"Quickbus message")
    
    toptree:add_le(quickbus_proto.fields.talker, buffer(0,2));

    local canIdTree=toptree:add_le(quickbus_proto.fields.messagekind, canIdBuf)
    if(canIdBuf:le_uint()==0x06c1) then
        toptree:add_le(quickbus_proto.fields.chainout, buffer(2,4));
        toptree:add_le(quickbus_proto.fields.measurementunit, buffer(6,2));
        pinfo.cols.info:set("Length of chain out ")
    else
        toptree:add_le(quickbus_proto.fields.unknown, buffer(2))
        
    end
    
--     canIdTree:add_le(quickbus_proto.fields.messagekind, canIdBuf);
--     canIdTree:add_le(quickbus_proto.fields.deviceid, canIdBuf)

end --function

DissectorTable.get("can.subdissector"):add_for_decode_as(quickbus_proto)
