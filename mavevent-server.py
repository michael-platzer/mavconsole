#!/usr/bin/env python3

import asyncio
import threading
import queue
import websockets
import json
import argparse


###############################################################################
# PARSE SELECT EVENTS FROM MAVLINK STREAM

from pymavlink import mavutil

MAVEVENT_PARSE_FUNCS = {
    # https://mavlink.io/en/messages/common.html#GLOBAL_POSITION_INT
    'GLOBAL_POSITION_INT': lambda msg: {'ua_pos': {
        'lat': msg.lat / 10**7, 'lon': msg.lon / 10**7, 'alt': msg.alt / 1000,
        'vlat': msg.vx / 100, 'vlon': msg.vy / 100, 'vz': -msg.vz / 100
    }},
    # https://mavlink.io/en/messages/common.html#GLOBAL_POSITION_INT_COV
    'GLOBAL_POSITION_INT_COV': lambda msg: {'ua_pos': {
        'lat': msg.lat / 10**7, 'lon': msg.lon / 10**7, 'alt': msg.alt / 1000,
        'vlat': msg.vx / 100, 'vlon': msg.vy / 100, 'vz': -msg.vz / 100
    }},
}

def mavevent_recv(connection_str, event_queue):
    '''
    Parse select messages from a MAVLink stream and add them to a queue
    '''
    mavconn = mavutil.mavlink_connection(connection_str)
    mavconn.wait_heartbeat()
    while True:
        msg = mavconn.recv_match(
            type=list(MAVEVENT_PARSE_FUNCS.keys()), blocking=True
        )
        if not msg or msg.get_type() == 'BAD_DATA':
            continue
        parse_func = MAVEVENT_PARSE_FUNCS.get(msg.get_type(), None)
        if parse_func is not None:
            event_queue.put(parse_func(msg))


###############################################################################
# SERVE EVENTS VIA WEBSOCKETS

mavevent_connections = set() # set of active websocket connections
mavevent_state       = {}    # current state accumulated from prior events

async def mavevent_session(websocket, path):
    '''
    Handle a websocket session for a client waiting for events
    '''
    mavevent_connections.add(websocket)
    try:
        # send current state
        await websocket.send(json.dumps(mavevent_state))
        # wait until the client disconnects
        await websocket.wait_closed()
    finally:
        mavevent_connections.remove(websocket)

async def mavevent_serve(event_queue, host=None, port=None):
    '''
    Serve events read from a queue via websockets
    '''
    async with websockets.serve(mavevent_session, host, port):
        while True:
            try:
                event = event_queue.get_nowait()
                mavevent_state.update(event)
                #websockets.broadcast(mavevent_connections, json.dumps(event))
                event_str = json.dumps(event)
                for conn in mavevent_connections:
                    await conn.send(event_str)
            except queue.Empty:
                await asyncio.sleep(0.001)


###############################################################################
# ARGUMENT PARSING AND INITIALIZATION

argparser = argparse.ArgumentParser(
    description='Serve select events from a MAVLink stream via websockets'
)
argparser.add_argument(
    '--host', nargs='?', default=None,
    help=(
        'Network interfaces on which the websocket server listens, '
        'see https://websockets.readthedocs.io/en/stable/reference/server.html'
    )
)
argparser.add_argument(
    '-p', '--port', nargs='?', default=8000,
    help='TCP port on which the server websocket server listens'
)
argparser.add_argument(
    'connection_string', metavar='CONNECTION_STRING',
    help=(
        'MAVLink connection string, '
        'see https://mavlink.io/en/mavgen_python/#connection_string'
    )
)
args = argparser.parse_args()

mavevent_queue = queue.SimpleQueue()
threading.Thread(
    target=mavevent_recv, args=(args.connection_string, mavevent_queue),
    daemon=True
).start()
asyncio.run(mavevent_serve(mavevent_queue, args.host, args.port))
