"""
A minimal API to speak OP_MSG to a driver.
"""

import bson
import struct
import asyncio
from dataclasses import dataclass

"""
Specified format of OP_MSG:

struct Section {
    uint8 payloadType;
    union payload {
        document  document; // payloadType == 0
        struct sequence {   // payloadType == 1
            int32      size;
            cstring    identifier;
            document*  documents;
        };
    };
};

struct OP_MSG {
    struct MsgHeader {
        int32  messageLength;
        int32  requestID;
        int32  responseTo;
        int32  opCode = 2013;
    };
    uint32      flagBits;
    Section+    sections;
    [uint32     checksum;]
};
"""

@dataclass
class opmsg:
    requestId: int
    responseTo: int
    payload0_document: dict

    def _to_bytes(self) -> bytes:
        out = bytearray()

        # Serialize header.
        out += struct.pack("<i", 0)  # Placeholder for `messageLength`
        out += struct.pack("<i", self.requestId)  # requestID
        out += struct.pack("<i", self.responseTo)  # responseTo
        out += struct.pack("<i", 2013)  # opCode
        out += struct.pack("<I", 0)  # flagBits
        # Serialize payload 0 section
        out += struct.pack("<B", 0)
        out += bson.encode(self.payload0_document)

        out[0:4] = struct.pack("<i", len(out))  # Overwrite `messageLength`
        return out

    def _from_bytes(msg: bytes):
        _messageLength = struct.unpack("<i", msg[0:4])
        msg = msg[4:]
        requestId = struct.unpack("<i", msg[0:4])[0]
        msg = msg[4:]
        responseTo = struct.unpack("<i", msg[0:4])[0]
        msg = msg[4:]
        opCode = struct.unpack("<i", msg[0:4])[0]
        if opCode != 2013:
            raise Exception("Expected to parse opCode 2013, got: {}. To force OP_MSG in the driver, set server API version".format(opCode))
        msg = msg[4:]
        _flagBits = struct.unpack("<I", msg[0:4])
        msg = msg[4:]
        payloadType = msg[0]
        if payloadType != 0:
            raise Exception("Expected to parse payloadType 0, got: {}".format(payloadType))
        msg = msg[1:]
        document_length = struct.unpack("<i", msg[0:4])[0]
        document = bson.decode(msg[0:document_length])
        return opmsg(requestId, responseTo, document)


async def recv(reader: asyncio.StreamReader) -> opmsg | None:
    """
    Receive an OP_MSG. Returns opmsg object or None. Ignores payload 1 document sequences.
    """
    try:
        msg_size_le = await reader.readexactly(4)
    except asyncio.IncompleteReadError as ire:
        if len(ire.partial) == 0:
            # Peer closed.
            return None
        else:
            # Unexpected. Re-raise.
            raise ire
        
    (msg_size,) = struct.unpack("<i", msg_size_le)
    remaining = await reader.readexactly(msg_size - 4)
    msg = msg_size_le + remaining
    return opmsg._from_bytes(msg)

async def send(writer: asyncio.StreamWriter, responseTo: int, payload0_document : dict) -> dict:
    msg = opmsg(0, responseTo, payload0_document)
    writer.write(msg._to_bytes())
    await writer.drain()

