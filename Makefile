
MAVLINK_PATH := $(abspath mavlink/)

test:
	PYTHONPATH=$(MAVLINK_PATH) python3 mavlink/pymavlink/tools/mavplayback.py *.tlog &
	sleep 1
	PYTHONPATH=$(MAVLINK_PATH) python3 mavevent-server.py
