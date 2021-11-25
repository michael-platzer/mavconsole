#!/usr/bin/env python3

import asyncio
import threading
import queue
import websockets
import json

from pymavlink import mavutil

mavevent_queue = queue.SimpleQueue()

MAVEVENT_MESSAGES = {
    # https://mavlink.io/en/messages/common.html#GLOBAL_POSITION_INT
    'GLOBAL_POSITION_INT': lambda msg: {
        'lat': msg.lat / 10**7, 'lon': msg.lon / 10**7, 'alt': msg.alt / 1000,
        'vlat': msg.vx / 100, 'vlon': msg.vy / 100, 'vz': -msg.vz / 100
    },
    # https://mavlink.io/en/messages/common.html#GLOBAL_POSITION_INT_COV
    'GLOBAL_POSITION_INT_COV': lambda msg: {
        'lat': msg.lat / 10**7, 'lon': msg.lon / 10**7, 'alt': msg.alt / 1000,
        'vlat': msg.vx / 100, 'vlon': msg.vy / 100, 'vz': -msg.vz / 100
    },
}

def mavevent_recv():
    global mavevent_queue
    mavconn = mavutil.mavlink_connection('127.0.0.1:14550')
    mavconn.wait_heartbeat()
    while True:
        msg = mavconn.recv_match(type=list(MAVEVENT_MESSAGES.keys()), blocking=True)
        if not msg or msg.get_type() == 'BAD_DATA':
            continue
        print(f"Got a {msg.get_type()} message")
        parse_func = MAVEVENT_MESSAGES.get(msg.get_type(), None)
        if parse_func is not None:
            mavevent_queue.put(json.dumps(parse_func(msg)))


mavevent_connections = set()

async def mavevent_session(websocket, path):
    '''
    Handle a websocket session for a client waiting for MAVLink events
    '''
    global mavevent_connections
    mavevent_connections.add(websocket)
    try:
        # Send previous moves, in case the game already started.
        #await replay(websocket, game)
        # wait until the client disconnects (we do not expect to receive any data)
        await websocket.wait_closed()
    finally:
        mavevent_connections.remove(websocket)

async def mavevent_serve():
    '''
    Serve select MAVLink events via websockets
    '''
    global mavevent_connections
    global mavevent_queue
    async with websockets.serve(mavevent_session, 'localhost', 8000):
        while True:
            try:
                event = mavevent_queue.get_nowait()
                #websockets.broadcast(mavevent_connections, event)
                for conn in mavevent_connections:
                    await conn.send(event)
            except queue.Empty:
                await asyncio.sleep(0.001)


threading.Thread(target=mavevent_recv, daemon=True).start()
asyncio.run(mavevent_serve())
