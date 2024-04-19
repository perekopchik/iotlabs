from datetime import datetime
from domain.aggregated_data import AggregatedData
from domain.accelerometer import Accelerometer
from domain.gps import Gps
from domain.parking import Parking
from CustomReader import CustomReader

from typing import Iterable
from csv import DictReader
import uuid
import logging

logger = logging.getLogger()

INVALID_EXPORTED_DATA_EXCEPTION_MESSAGE = "Invalid exported data"
FILES_ALREADY_OPENED_EXCEPTION_MESSAGE = "Files already opened"
FILES_NOT_OPENED_EXCEPTION_MESSAGE = "Files not opened"

class FileDatasource:
    def __init__(
        self, accelerometer_filename: str, gps_filename: str, parking_filename: str
    ) -> None:
        self.accelerometer_filename = accelerometer_filename
        self.gps_filename = gps_filename
        self.parking_filename = parking_filename
        self.accelerometer_reader = None
        self.gps_reader = None
        self.parking_reader = None
        self.life_time_count = None
        self.time_index = None
        self.uuid = str(uuid.uuid4())

    def read(self) -> AggregatedData | None:
        if (
            self.accelerometer_reader is None
            or self.gps_reader is None
            or self.parking_reader is None
            or self.life_time_count is None
            or self.time_index is None
        ):
            return None

        while True:
            if self.time_index == self.life_time_count:
                self.stopReading()
                self.time_index = 0
                break

            p = self.time_index / self.life_time_count + 1e-4

            accelerometer_data_new_ind = int(self.accelerometer_reader.lines * p)
            gps_data_new_ind = int(self.gps_reader.lines * p)
            parking_data_new_ind = int(self.parking_reader.lines * p)

            accelerometer_data = self.accelerometer_reader.getCurOrNext(
                accelerometer_data_new_ind
            )
            gps_data = self.gps_reader.getCurOrNext(gps_data_new_ind)
            parking_data = self.parking_reader.getCurOrNext(parking_data_new_ind)

            if accelerometer_data is None or gps_data is None or parking_data is None:
                raise ValueError(INVALID_EXPORTED_DATA_EXCEPTION_MESSAGE)

            logger.debug(f"Accelerometer data: {accelerometer_data}")
            logger.debug(f"GPS data: {gps_data}")
            logger.debug(f"Parking data: {parking_data}")

            try:
                accelerometer_values = [
                    int(accelerometer_data["X"]),
                    int(accelerometer_data["Y"]),
                    int(accelerometer_data["Z"]),
                ]

                gps_values = [
                    float(gps_data["longitude"]),
                    float(gps_data["latitude"]),
                ]

                empty_count = int(parking_data["empty_count"])
                gps_parking = Gps(
                    float(parking_data["longitude"]), float(parking_data["latitude"])
                )
            except (ValueError, IndexError):
                logger.error(
                    f"Failed to parse data, Accelerometer data: {accelerometer_data}, GPS data: {gps_data}, Parking data: {parking_data}"
                )
                continue

            accelerometer = Accelerometer(*accelerometer_values)
            parking = Parking(empty_count, gps_parking)
            gps = Gps(*gps_values)

            timestamp = datetime.now()

            self.time_index += 1

            return AggregatedData(accelerometer, gps, parking, timestamp, self.uuid)

    def startReading(self, *args, **kwargs):
        if self.accelerometer_reader is not None or self.gps_reader is not None:
            raise ValueError(FILES_ALREADY_OPENED_EXCEPTION_MESSAGE)

        self.accelerometer_reader = CustomReader(self.accelerometer_filename)
        self.gps_reader = CustomReader(self.gps_filename)
        self.parking_reader = CustomReader(self.parking_filename)

        self.life_time_count = max(
            self.accelerometer_reader.lines,
            self.gps_reader.lines,
            self.parking_reader.lines,
        )

        self.time_index = 0

    def stopReading(self, *args, **kwargs):
        if (
            self.accelerometer_reader is None
            or self.gps_reader is None
            or self.parking_reader is None
        ):
            raise ValueError(FILES_NOT_OPENED_EXCEPTION_MESSAGE)

        self.accelerometer_reader.close()
        self.gps_reader.close()
        self.parking_reader.close()
