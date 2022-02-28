
MAVLINK_PATH := $(abspath mavlink/)

test:
	PYTHONPATH=$(MAVLINK_PATH) python3 mavlink/pymavlink/tools/mavplayback.py *.tlog &
	sleep 1
	PYTHONPATH=$(MAVLINK_PATH) python3 mavevent-server.py --host localhost --json util/airspace.geojson 127.0.0.1:14550
