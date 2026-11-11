"""Local PC/SC bridge for reading ACR122U card UIDs."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from smartcard.Exceptions import (
    CardConnectionException,
    NoCardException,
    NoReadersException,
)
from smartcard.System import readers

HOST = "127.0.0.1"
PORT = 8765
GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]


def read_uid() -> str | None:
    available_readers = readers()
    if not available_readers:
        raise NoReadersException("No PC/SC smart-card reader found")

    for _attempt in range(2):
        connection = available_readers[0].createConnection()
        try:
            connection.connect()
            data, sw1, sw2 = connection.transmit(GET_UID_APDU)
        except NoCardException:
            return None
        except CardConnectionException as exc:
            if "0x80100068" not in str(exc) or _attempt == 1:
                raise
            continue
        finally:
            try:
                connection.disconnect()
            except CardConnectionException:
                pass

        if (sw1, sw2) != (0x90, 0x00):
            raise RuntimeError(f"Reader returned status {sw1:02X}{sw2:02X}")
        return "".join(f"{byte:02X}" for byte in data)

    return None


class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/uid":
            self.send_error(404, "Use GET /uid")
            return

        try:
            uid = read_uid()
            payload = {"uid": uid}
            status = 200
        except (CardConnectionException, NoReadersException, RuntimeError) as exc:
            payload = {"error": str(exc)}
            status = 503

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        origin = self.headers.get("Origin", "")
        if origin in {"http://localhost", "http://127.0.0.1"}:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"ACR122U bridge listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), BridgeHandler).serve_forever()
