import http.server
import socketserver
import os

MOCK_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8124

class MockEtaRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve files from the mocketa directory
        rel_path = path.lstrip("/user/").rstrip("/") + ".xml"
        return os.path.join(MOCK_DIR, rel_path)

    def end_headers(self):
        # Always serve as XML for .xml files
        if self.path.endswith('.xml'):
            self.send_header('Content-Type', 'application/xml')
        super().end_headers()

if __name__ == "__main__":
    os.chdir(MOCK_DIR)
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("0.0.0.0", PORT), MockEtaRequestHandler) as httpd:
        print(f"Mock ETA server running at http://localhost:{PORT}/")
        httpd.serve_forever()
